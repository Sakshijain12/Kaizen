"""The Kaizen pipeline. Yields events so UIs / agents can stream progress.

  1. deps      parse pins, compare with PyPI               -> drift list
  2. baseline  Daytona: install UPGRADED deps, run tests    -> what breaks
  3. research  Tavily: release notes / migration guides     -> changelog text
  4. analyze   Nosana LLM: changelog x code x failures      -> structured breaking changes
  5. scan      regex scan of the repo                       -> exact affected lines
  6. rewrite   Nosana LLM / CodeAF harness / rules          -> patched files
  7. verify    Daytona: rerun tests, loop on failure        -> green or report
  8. report    unified diff + markdown report + fixed copy
"""
import difflib
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Iterator

from . import analyzer, changelog, config, deps, evidence, llm, rewriter, sandbox

TEXT_EXT = {".py", ".txt", ".toml", ".cfg", ".ini"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}


def ev(kind, step, msg, **data):
    return {"type": kind, "step": step, "message": msg, "data": data, "t": time.time()}


PUBLIC_GIT = re.compile(r"^https://(github\.com|gitlab\.com|bitbucket\.org)/[\w.-]+/[\w.-]+?(\.git)?/?$")
DEMO_REPO = config.ROOT / "demo_repo"


def load_repo(source: str) -> tuple[Path, str]:
    source = source.strip()
    if source in ("demo", "demo_repo", str(DEMO_REPO)):
        return DEMO_REPO, "demo_repo"
    if re.match(r"^(https?://|git@)", source):
        if config.PUBLIC_MODE and not PUBLIC_GIT.match(source):
            raise ValueError("Only public GitHub / GitLab / Bitbucket HTTPS repo URLs are supported")
        dest = Path(tempfile.mkdtemp(prefix="kaizen-src-"))
        subprocess.run(["git", "clone", "--depth", "1", "--single-branch", source, str(dest)],
                       check=True, capture_output=True, timeout=120,
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        return dest, source.rstrip("/").split("/")[-1].removesuffix(".git")
    if config.PUBLIC_MODE:  # never read the server's own filesystem for visitors
        raise ValueError("Paste a public git URL (local paths are disabled on the public site)")
    p = Path(source).expanduser().resolve()
    return p, p.name


def read_files(repo: Path) -> dict[str, str]:
    files = {}
    for f in repo.rglob("*"):
        if f.is_file() and f.suffix in TEXT_EXT and not (set(f.relative_to(repo).parts) & SKIP_DIRS):
            try:
                files[str(f.relative_to(repo))] = f.read_text()
            except UnicodeDecodeError:
                pass
    return files


def test_counts(output: str) -> dict:
    counts = {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed|error|errors)", output)}
    if "errors" in counts:
        counts["error"] = counts.pop("errors")
    return counts


def run(source: str) -> Iterator[dict]:
    started = time.time()
    repo, name = load_repo(source)
    files = read_files(repo)
    st = config.status()
    yield ev("info", "setup", f"Loaded {name}: {len(files)} files", status=st, llm=llm.label())

    # 1. dependency drift --------------------------------------------------
    yield ev("start", "deps", "Checking pinned dependencies against PyPI")
    drifts = deps.find_drift(repo)
    if not drifts:
        yield ev("done", "deps", "All dependencies are up to date — nothing to do")
        yield ev("result", "report", "No drift", ok=True, drifts=[])
        return
    yield ev("done", "deps", ", ".join(f"{d.name} {d.current} → {d.latest}" for d in drifts),
             drifts=[d.as_dict() for d in drifts])
    versions = ", ".join(f"{d.name}=={d.latest}" for d in drifts)
    files["requirements.txt"] = deps.upgraded_requirements(repo, drifts)

    # 2. baseline: upgraded deps, original code --------------------------
    yield ev("start", "baseline", "Spinning up sandbox and running tests with upgraded deps")
    runner = sandbox.make_runner()
    try:
        yield ev("log", "baseline", f"Sandbox: {runner.label} ({runner.id})")
        runner.write_files(files)
        code, out = runner.install()
        if code != 0:
            yield ev("fail", "baseline", "Dependency install failed in sandbox", output=out[-3000:])
            return
        code, base_out = runner.run_tests()
        base = test_counts(base_out)
        if code == 0:
            yield ev("done", "baseline", f"Tests already pass on {versions} — safe to upgrade", counts=base)
        else:
            yield ev("done", "baseline", f"Upgrade breaks the build: {base}", counts=base, output=base_out[-4000:])

        # 3 + 4. research + analyze, per drifted package ------------------
        changes, sources = [], []
        code_only = {p: c for p, c in files.items() if p.endswith(".py")}
        for d in drifts:
            yield ev("start", "research", f"Researching {d.name} {d.latest} changelog")
            cl = changelog.research(d.name, d.current, d.latest)
            sources += [dict(s, package=d.name) for s in cl["sources"]]
            src = "Tavily" if cl["live"] else "offline notes (set TAVILY_API_KEY)"
            yield ev("done", "research", f"{d.name}: {len(cl['sources'])} sources via {src}",
                     sources=cl["sources"], chars=len(cl["text"]))

            yield ev("start", "analyze", f"Extracting breaking changes for {d.name}")
            found, engine = analyzer.analyze(d.name, d.current, d.latest, cl["text"], code_only, base_out)
            changes += found
            yield ev("done", "analyze", f"{d.name}: {len(found)} breaking changes ({engine})", changes=found)
            cited = evidence.attach(found, cl["text"])
            yield ev("done", "evidence", f"{d.name}: cited changelog passages via {cited}",
                     evidence=[{"symbol": c["symbol"], "evidence": c.get("evidence", ""),
                                "score": c.get("evidence_score")} for c in found])

        # 5. scan ---------------------------------------------------------
        hits = analyzer.scan(code_only, changes)
        yield ev("done", "scan", f"{len(hits)} affected lines in {len({h['file'] for h in hits})} files", hits=hits)

        if code == 0 and not hits:
            yield ev("result", "report", "Upgrade is safe", ok=True, drifts=[d.as_dict() for d in drifts],
                     changes=changes, hits=hits, baseline=base, final=base, attempts=0, diffs={},
                     sources=sources, elapsed=time.time() - started)
            return

        # 6 + 7. rewrite / verify loop -------------------------------------
        patched = dict(files)
        last_out, final, ok, attempt = base_out, base, code == 0, 0
        notes = {}
        while not ok and attempt < config.MAX_FIX_ATTEMPTS:
            attempt += 1
            targets = {h["file"] for h in analyzer.scan({p: patched[p] for p in code_only}, changes)}
            targets |= rewriter.failing_files(last_out, code_only)
            targets = sorted(targets) or sorted(p for p in code_only if not p.startswith("tests"))
            yield ev("start", "rewrite", f"Attempt {attempt}: rewriting {', '.join(targets)}")

            updates = {}
            if config.REWRITE_ENGINE == "codeaf":
                try:
                    updates = rewriter.rewrite_codeaf(patched, targets, changes, last_out, versions)
                    for t in updates:
                        notes[t] = "rewritten by CodeAF harness"
                except Exception as e:
                    yield ev("log", "rewrite", f"CodeAF unavailable ({e}); falling back")
            for t in targets:
                if t in updates:
                    continue
                new, why = None, ""
                if llm.available():
                    try:
                        new, why = rewriter.rewrite_llm(t, patched[t], changes, last_out, versions)
                        why = f"{llm.label()}: {why}"
                    except Exception as e:
                        yield ev("log", "rewrite", f"LLM rewrite of {t} failed ({e}); using rules")
                if new is None:
                    new, why = rewriter.rewrite_rules(patched[t], changes)
                if new != patched[t]:
                    updates[t] = new
                    notes[t] = why
            patched.update(updates)
            yield ev("done", "rewrite", f"Attempt {attempt}: changed {len(updates)} files",
                     notes={k: notes[k] for k in updates})

            yield ev("start", "verify", f"Attempt {attempt}: re-running tests in sandbox")
            runner.write_files(updates)
            rc, last_out = runner.run_tests()
            final, ok = test_counts(last_out), rc == 0
            yield ev("done" if ok else "fail", "verify",
                     ("All tests pass ✅" if ok else f"Still failing: {final}"), counts=final,
                     output=last_out[-3000:])
            if not updates and not ok:
                break
    finally:
        runner.close()

    # 8. report --------------------------------------------------------------
    diffs = {}
    for p, new in patched.items():
        old = (repo / p).read_text() if (repo / p).exists() else ""
        if new != old:
            diffs[p] = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                    f"a/{p}", f"b/{p}"))
    out_dir = config.OUTPUT_DIR / f"{name}-fixed"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(repo, out_dir, ignore=shutil.ignore_patterns(*SKIP_DIRS))
    for p, c in patched.items():
        (out_dir / p).parent.mkdir(parents=True, exist_ok=True)
        (out_dir / p).write_text(c)
    patch_path = config.OUTPUT_DIR / f"{name}.patch"
    patch_path.write_text("".join(diffs.values()))

    result = dict(ok=ok, drifts=[d.as_dict() for d in drifts], changes=changes, hits=hits,
                  baseline=base, final=final, attempts=attempt, diffs=diffs, notes=notes,
                  sources=sources, patch_path=str(patch_path), fixed_dir=str(out_dir),
                  sandbox=runner.label, llm=llm.label(), elapsed=round(time.time() - started, 1))
    (config.OUTPUT_DIR / f"{name}-report.md").write_text(render_report(name, result))
    yield ev("result", "report", "Fixed ✅" if ok else "Partially fixed — needs human review", **result)


def render_report(name: str, r: dict) -> str:
    lines = [f"# Kaizen upgrade report: {name}", "",
             f"**Result:** {'✅ tests green after upgrade' if r['ok'] else '⚠️ needs review'}  ",
             f"**Tests:** before {r['baseline']} → after {r['final']} in {r['attempts']} attempt(s)  ",
             f"**Sandbox:** {r['sandbox']} · **Model:** {r['llm']} · {r['elapsed']}s", "",
             "## Upgrades", *[f"- `{d['name']}` {d['current']} → {d['latest']}" for d in r["drifts"]], "",
             "## Breaking changes that hit this repo",
             *[f"- **{c['package']} {c['version']}** `{c['symbol']}` → `{c['replacement']}` — {c['description']}"
               + (f"\n  > {c['evidence'][:300].replace(chr(10), ' ')}" if c.get("evidence") else "")
               for c in r["changes"]], "",
             "## Affected lines", *[f"- `{h['file']}:{h['line']}` `{h['code']}`" for h in r["hits"]], "",
             "## Sources", *[f"- [{s['title'] or s['url']}]({s['url']})" for s in r["sources"]], "",
             "## Patch", "```diff", "".join(r["diffs"].values()), "```"]
    return "\n".join(lines)

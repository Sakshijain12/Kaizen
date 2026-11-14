"""Rewrite affected files. Engines: Nosana LLM (default), CodeAF harness, offline rules."""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config, knowledge, llm

SYSTEM = """You migrate Python code to new library versions.
Rewrite the file so it works with the NEW versions, applying the listed breaking changes.
Keep behaviour identical, keep the public function names and signatures, change as little as possible.
Reply with the COMPLETE updated file in a single ```python code block, then one line starting with
'WHY:' summarising what you changed."""


def _changes_text(changes):
    return "\n".join(f"- {c['package']} {c['version']}: `{c['symbol']}` -> `{c['replacement']}` ({c['description']})"
                     for c in changes)


def rewrite_llm(path: str, content: str, changes: list[dict], test_output: str, versions: str) -> tuple[str, str]:
    user = (f"Target versions: {versions}\n\nBreaking changes:\n{_changes_text(changes)}\n\n"
            f"Latest test failures:\n{test_output[-3500:]}\n\nFILE {path}:\n```python\n{content}\n```")
    reply = llm.chat(SYSTEM, user)
    code = llm.extract_code(reply)
    if not code:
        raise ValueError("model reply had no code block")
    why = re.search(r"WHY:\s*(.+)", reply)
    return code.rstrip() + "\n", (why.group(1).strip() if why else "rewritten by LLM")


def rewrite_rules(content: str, changes: list[dict]) -> tuple[str, str]:
    applied = []
    rules = {c["symbol"]: c.get("rule") for c in changes}
    # LLM-produced changes have no regex rule; borrow the offline rule for the same symbol if we know one.
    for c in changes:
        if not rules.get(c["symbol"]):
            for k in knowledge.offline_changes(c["package"], c["version"]):
                if k["symbol"] == c["symbol"]:
                    rules[c["symbol"]] = k["rule"]
    for sym, rule in rules.items():
        if not rule:
            continue
        new = re.sub(rule[0], rule[1], content)
        if new != content:
            applied.append(sym)
            content = new
    return content, ("applied rules: " + ", ".join(applied)) if applied else "no rule matched"


def rewrite_codeaf(files: dict[str, str], targets: list[str], changes: list[dict],
                   test_output: str, versions: str) -> dict[str, str]:
    """Hand the job to AgentField's CodeAF harness (headless `codeaf do`)."""
    if not shutil.which(config.CODEAF_BIN):
        raise FileNotFoundError("codeaf binary not found — install: curl -fsSL https://agentfield.ai/get/codeaf | bash")
    work = Path(tempfile.mkdtemp(prefix="codeaf-"))
    for rel, c in files.items():
        (work / rel).parent.mkdir(parents=True, exist_ok=True)
        (work / rel).write_text(c)
    task = (f"Migrate this repo to {versions}. Apply these breaking changes:\n{_changes_text(changes)}\n"
            f"Focus on files: {', '.join(targets)}. Do not change test expectations. "
            f"Current failing tests:\n{test_output[-2500:]}")
    subprocess.run([config.CODEAF_BIN, "do", task, "--timeout", "10m", "--json"],
                   cwd=work, capture_output=True, text=True, timeout=700)
    out = {}
    for rel, old in files.items():
        new = (work / rel).read_text() if (work / rel).exists() else old
        if new != old:
            out[rel] = new
    shutil.rmtree(work, ignore_errors=True)
    return out


def is_test(rel: str) -> bool:
    """Never rewrite tests from failure tracebacks — they are the spec we must satisfy."""
    name = rel.rsplit("/", 1)[-1]
    return rel.startswith("tests/") or name.startswith("test_") or name.endswith("_test.py")


def failing_files(test_output: str, repo_files: dict[str, str]) -> set[str]:
    found = set()
    for m in re.finditer(r"([\w./\\-]+\.py):\d+", test_output):
        p = m.group(1).replace("\\", "/")
        for rel in repo_files:
            if p.endswith(rel) and not is_test(rel):
                found.add(rel)
    return found

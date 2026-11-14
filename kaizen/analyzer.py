"""Turn raw changelog text into structured breaking changes that affect THIS repo."""
import re

from . import knowledge, llm

SYSTEM = """You are a senior Python maintainer doing a dependency upgrade.
You read release notes / migration guides and identify ONLY the breaking changes
(removed, renamed, or behaviour-changed APIs) that the given project code actually uses.
Respond with a JSON array only. Each item:
{"symbol": "...", "search_pattern": "<Python regex that matches the old usage in code>",
 "replacement": "<the new API to use>", "description": "<one sentence>", "source_url": "<url or empty>"}
Return [] if nothing in the code is affected."""


def analyze(package: str, current: str, latest: str, changelog_text: str,
            code: dict[str, str], test_output: str) -> tuple[list[dict], str]:
    """Return (changes, engine_label)."""
    if not llm.available():
        return knowledge.offline_changes(package, latest), "offline-rules"

    code_blob = "\n\n".join(f"# FILE: {p}\n{c}" for p, c in code.items())[:9000]
    user = (
        f"Package: {package}, upgrading {current} -> {latest}\n\n"
        f"=== RELEASE NOTES / MIGRATION DOCS (from web research) ===\n{changelog_text}\n\n"
        f"=== PROJECT CODE ===\n{code_blob}\n\n"
        f"=== TEST OUTPUT AFTER UPGRADE ===\n{test_output[-4000:]}\n\n"
        f"List the breaking changes in {package} that affect this code."
    )
    try:
        items = llm.parse_json(llm.chat(SYSTEM, user))
        if isinstance(items, dict):
            items = items.get("changes", [items])
        changes = []
        for it in items:
            if not isinstance(it, dict) or not it.get("symbol"):
                continue
            pat = it.get("search_pattern") or re.escape(it["symbol"].split(".")[-1])
            try:
                re.compile(pat)
            except re.error:
                pat = re.escape(it["symbol"].split(".")[-1])
            changes.append({
                "package": package, "version": latest, "symbol": it["symbol"],
                "search_pattern": pat, "replacement": it.get("replacement", ""),
                "description": it.get("description", ""), "source_url": it.get("source_url", ""),
            })
        return changes, llm.label()
    except Exception as e:  # model hiccup: degrade gracefully, never kill the demo
        fallback = knowledge.offline_changes(package, latest)
        return fallback, f"offline-rules (LLM error: {e.__class__.__name__})"


def scan(code: dict[str, str], changes: list[dict]) -> list[dict]:
    """Find every line in the repo hit by a breaking change."""
    hits = []
    for ch in changes:
        rx = re.compile(ch["search_pattern"])
        for path, content in code.items():
            for n, line in enumerate(content.splitlines(), 1):
                if rx.search(line):
                    hits.append({"file": path, "line": n, "code": line.strip(),
                                 "symbol": ch["symbol"], "package": ch["package"]})
    return hits

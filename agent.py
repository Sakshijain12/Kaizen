"""AgentField node "kaizen": exposes the Kaizen upgrade agent as reasoners/skills on the control plane.

  af server                # terminal 1 — control plane + dashboard on :8080
  python agent.py          # terminal 2 — registers node "kaizen"

  curl -X POST http://localhost:8080/api/v1/execute/kaizen.fix_repo \
       -H 'Content-Type: application/json' -d '{"input": {"repo": "demo_repo"}}'
"""
import asyncio
from pathlib import Path

from pydantic import BaseModel

from agentfield import Agent, AIConfig, HarnessConfig
from kaizen import changelog, config, deps, pipeline

# LLM: Nosana's OpenAI-compatible inference, routed through AgentField's LiteLLM layer.
try:
    from kaizen import llm
    _, _model, _ = llm.backend()
except Exception:
    _model = config.NOSANA_MODEL or "auto"

app = Agent(
    node_id="kaizen",
    description="Watches dependency changelogs, finds breaking changes, rewrites code, verifies in Daytona.",
    tags=["dependencies", "migration", "tavily", "daytona", "nosana", "codeaf"],
    ai_config=AIConfig(model=f"openai/{_model}", api_base=config.NOSANA_BASE_URL,
                       api_key=config.NOSANA_API_KEY or None, temperature=0.1),
    # CodeAF is AgentField's native coding harness; used by migrate_with_codeaf below.
    harness_config=HarnessConfig(provider="codeaf", codeaf_bin=config.CODEAF_BIN),
)


class BreakingChange(BaseModel):
    symbol: str
    search_pattern: str
    replacement: str
    description: str


class BreakingChanges(BaseModel):
    changes: list[BreakingChange]


@app.skill(tags=["deps"])
def check_drift(repo: str) -> dict:
    """Pinned deps vs. latest PyPI releases."""
    return {"drifts": [d.as_dict() for d in deps.find_drift(Path(repo).expanduser())]}


@app.skill(tags=["tavily"])
def research_changelog(package: str, current: str, latest: str) -> dict:
    """Tavily search + extract of release notes / migration guides."""
    return changelog.research(package, current, latest)


@app.reasoner(tags=["nosana", "analysis"])
async def extract_breaking_changes(package: str, latest: str, changelog_text: str, code: str) -> dict:
    """Nosana-hosted model reads changelog x code and returns structured breaking changes."""
    result = await app.ai(
        system="Identify breaking changes in the release notes that affect the given code.",
        user=f"{package} {latest}\n\nRELEASE NOTES:\n{changelog_text[:10000]}\n\nCODE:\n{code[:8000]}",
        schema=BreakingChanges,
    )
    return result.model_dump()


@app.reasoner(tags=["pipeline", "daytona"])
async def fix_repo(repo: str) -> dict:
    """Full pipeline: drift -> Daytona baseline -> Tavily -> analyze -> rewrite -> Daytona verify."""
    events = await asyncio.to_thread(lambda: list(pipeline.run(repo)))
    for e in events:
        if e["type"] in ("done", "fail"):
            app.note(f"[{e['step']}] {e['message']}", tags=[e["step"]])
    result = events[-1]["data"]
    result.pop("diffs", None)  # big; the patch file path is returned instead
    return {"summary": events[-1]["message"], **result}


@app.reasoner(tags=["codeaf"])
async def migrate_with_codeaf(repo: str, instructions: str) -> dict:
    """Delegate a free-form migration to the CodeAF harness inside the repo directory."""
    res = await app.harness(instructions, cwd=str(Path(repo).expanduser().resolve()), max_turns=30)
    return {"result": getattr(res, "result", str(res))}


if __name__ == "__main__":
    app.run()

# 🔴 Kaizen (改善): the self-upgrading codebase agent

> *Kaizen* is Japanese for "continuous improvement". Your dependencies upgrade themselves: researched, rewritten and proven in a sandbox.

**An AI agent that watches your dependencies' changelogs, finds the breaking changes that hit *your* code, rewrites it, and proves the fix by running your tests in a sandbox.**

Every team pins dependencies and falls behind, because upgrading means reading release notes, finding every
affected call site, and hoping the tests catch the rest. Upgrades that get skipped turn into security
and maintenance debt. Kaizen does the whole loop on its own and hands back a verified patch, with
every change cited to the release notes that justify it.

```
requirements.txt ──► PyPI drift ──► Daytona: install new versions, run tests (what breaks?)
                                        │
          Tavily: search + extract release notes / migration guides
                                        │
          Analyze: changelog × your code × failing tests ──► structured breaking changes
          Nosana embeddings: cite the exact changelog passage for each change
                                        │
          Scan: exact affected lines ──► Rewrite (Nosana LLM / CodeAF harness / rules)
                                        │
          Daytona: re-run tests ──► still failing? feed errors back, retry (max 3)
                                        │
                     ✅ verified patch + report + fixed copy of the repo
```

## Demo

`demo_repo/` is a small sales-analytics module pinned to `numpy==1.26.4` and `pandas==1.5.3`.
After upgrading to numpy 2.x / pandas 3.x, **all 4 tests fail** (`np.float_`, `np.NaN`,
`DataFrame.append`, `DataFrame.iteritems`, and the pandas 3.0 `str` dtype breaking `np.issubdtype`).
The agent fixes them and the tests go **green in about 40 seconds**, with the tests running in a real Daytona sandbox.

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # add your keys
.venv/bin/streamlit run app.py  # live UI
.venv/bin/python cli.py demo_repo                  # or the CLI
.venv/bin/python cli.py https://github.com/you/repo  # any public Python repo with requirements.txt + pytest
```

Outputs are written to `output/`: `<repo>.patch`, `<repo>-report.md` and `<repo>-fixed/`.

## The website

`streamlit run app.py` starts the Kaizen web app, where anyone can use the agent:

- **⚡ Upgrade a repo**: try the built-in demo or paste a public GitHub / GitLab / Bitbucket URL. Each of the 8 agent steps streams live, with a progress bar, the sandbox test output and a timer.
- **Result dashboard**: shows upgrades, breaking changes, tests before → after, and run time. Below that are tabs for the **patch** (with a download button and a `git apply` hint), **breaking changes** (each with the affected lines in your code and a cited release-note quote), **sources**, and a downloadable **Markdown report** you can paste into a pull request.
- **🧭 How it works**: 8 step cards, each labelled with the partner that does that step, plus the architecture.
- **ℹ️ About**: why it exists, privacy and safety, the stack, the roadmap and the team.
- **Sidebar**: live status for each partner integration (green = live, amber = fallback) and a per-visitor run counter.

### Hosting it for other users (`PUBLIC_MODE=1`)

Public mode switches on the safety rails for strangers' code:
- **Local paths are disabled.** Visitors can only submit public HTTPS git URLs on GitHub, GitLab or Bitbucket.
- **Daytona is required.** Visitor code never runs on the host machine; without a Daytona key the run is refused.
- **Runs are limited.** Each browser session gets `MAX_RUNS_PER_SESSION` runs (default 5).

**Streamlit Community Cloud** (free):
1. Push the repo to GitHub.
2. On share.streamlit.io, choose New app → this repo → `app.py`. Under *Advanced settings*, pick **Python 3.13**.
3. Paste the secrets below. Root-level Streamlit secrets become environment variables, so no code changes are needed.
   ```toml
   PUBLIC_MODE = "1"
   NOSANA_API_KEY = "nos_..."
   DAYTONA_API_KEY = "dtn_..."
   TAVILY_API_KEY = "tvly-..."
   ```

## Partner tech: where each one is used in the code

| Partner | Role | Code |
|---|---|---|
| **Daytona** | Every test run happens in a fresh, isolated sandbox: upload repo → `pip install` upgraded deps → `pytest` (baseline) → upload patched files → `pytest` again in the retry loop → delete. | [`driftfixer/sandbox.py`](driftfixer/sandbox.py) `DaytonaRunner` (`Daytona().create`, `fs.upload_files`, `process.exec`, `sandbox.delete`) |
| **Tavily** | Live changelog research: `search(search_depth="advanced", include_answer=...)` finds release notes and migration guides, then `extract(query=..., chunks_per_source=5)` pulls the relevant parts of the full pages. | [`driftfixer/changelog.py`](driftfixer/changelog.py) |
| **Nosana** | Decentralized GPU inference through the OpenAI-compatible endpoint `inference.nosana.com/v1`. **Embeddings** (`nemotron-3-embed-1b`) rank the Tavily passages to cite evidence for each breaking change. A **chat model**, when one is live (auto-detected from `/v1/models`), does breaking-change analysis and code rewriting. | [`driftfixer/evidence.py`](driftfixer/evidence.py), [`driftfixer/llm.py`](driftfixer/llm.py), [`driftfixer/analyzer.py`](driftfixer/analyzer.py), [`driftfixer/rewriter.py`](driftfixer/rewriter.py) |
| **AgentField / CodeAF** | The agent is an AgentField node (`docs-drift-fixer`) with skills `check_drift` and `research_changelog`, and reasoners `extract_breaking_changes` (`app.ai` → Nosana through LiteLLM with a Pydantic schema), `fix_repo` (the full pipeline, progress through `app.note`) and `migrate_with_codeaf` (`app.harness` → **CodeAF**). Set `REWRITE_ENGINE=codeaf` to make CodeAF (`codeaf do ... --json`) the rewrite engine in the pipeline. | [`agent.py`](agent.py), [`driftfixer/rewriter.py`](driftfixer/rewriter.py) `rewrite_codeaf` |

### Run as an AgentField agent

```bash
curl -fsSL https://agentfield.ai/install.sh | bash     # af control plane + CodeAF
af server                                               # terminal 1, dashboard on :8080
.venv/bin/python agent.py                               # terminal 2, registers the node
curl -X POST http://localhost:8080/api/v1/execute/docs-drift-fixer.fix_repo \
  -H 'Content-Type: application/json' -d '{"input": {"repo": "demo_repo"}}'
```

## Design choices

- **Tests are the spec.** The agent never rewrites test files from failure tracebacks. It only changes code until the existing tests pass on the new versions.
- **The analysis is specific to your repo.** The model sees the changelog, your code and the actual failures together, so it reports the changes that affect you rather than every change in the release.
- **Every change has a citation.** Each breaking change carries the changelog passage that justifies it, ranked by Nosana embeddings.
- **Graceful degradation.** Missing keys or a model hiccup never kill the demo: a local venv stands in for Daytona, curated notes stand in for Tavily, and known rewrite rules stand in for the LLM. The UI shows which mode each partner is running in.

## Roadmap

- Run as a GitHub App on a schedule, opening one PR per upgrade with the report as the PR body
- npm / Cargo / Go modules
- Self-deployed vLLM coder model on Nosana GPU markets for private repos

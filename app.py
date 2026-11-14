"""Kaizen — the self-upgrading codebase agent.  Run:  streamlit run app.py"""
import html
import time

import streamlit as st

from driftfixer import config, evidence, llm, pipeline

APP_NAME = "Kaizen"
TAGLINE = "Your dependencies upgrade themselves: researched, rewritten and proven in a sandbox."
TEAM = []  # e.g. [("Your Name", "role", "https://github.com/you")]
REPO_URL = ""  # e.g. "https://github.com/you/kaizen"

st.set_page_config(page_title=f"{APP_NAME} · self-upgrading codebase agent", page_icon="🔴",
                   layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------- styles
st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1180px;}
.hero {border-radius: 18px; padding: 34px 38px; margin-bottom: 18px; color: #fff;
  background: radial-gradient(circle at 88% 20%, rgba(255,255,255,.18) 0 70px, transparent 71px),
              linear-gradient(120deg, #1c1b1a 0%, #3a1016 55%, #c8102e 100%);}
.hero h1 {font-size: 2.6rem; margin: 0 0 4px 0; color: #fff; letter-spacing: -.5px;}
.hero h1 .jp {font-size: 1.1rem; opacity: .75; margin-left: 10px; font-weight: 400;}
.hero p {font-size: 1.12rem; opacity: .92; margin: 0; max-width: 760px;}
.chips {margin-top: 16px;}
.chip {display: inline-block; padding: 5px 12px; border-radius: 999px; margin: 0 6px 6px 0;
  font-size: .82rem; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.25);}
.card {background: #fff; border: 1px solid #e7e2da; border-radius: 14px; padding: 18px 18px 14px;
  height: 100%;}
.card h4 {margin: 0 0 6px 0; font-size: 1rem;}
.card p {margin: 0; color: #55514c; font-size: .9rem;}
.num {display: inline-flex; width: 26px; height: 26px; border-radius: 50%; align-items: center;
  justify-content: center; background: #c8102e; color: #fff; font-size: .8rem; margin-right: 8px;}
.badge {display: inline-block; font-size: .72rem; padding: 2px 8px; border-radius: 6px;
  background: #f1eee8; color: #5b544c; margin-top: 8px; border: 1px solid #e2dcd2;}
.dot {display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 7px;}
.on {background: #1f9d55;} .off {background: #d0a000;}
.result-ok {background: #ecf8f0; border: 1px solid #b7e2c5; border-radius: 14px; padding: 16px 20px;}
.result-warn {background: #fff6e6; border: 1px solid #f0d49b; border-radius: 14px; padding: 16px 20px;}
.quote {border-left: 3px solid #c8102e; padding: 6px 12px; color: #4a4540; background: #fbf8f4;
  font-size: .86rem; border-radius: 0 8px 8px 0; margin: 4px 0 12px;}
.footer {text-align: center; color: #8a847b; font-size: .82rem; margin-top: 40px;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- state
ss = st.session_state
ss.setdefault("runs", 0)
ss.setdefault("result", None)
ss.setdefault("events", [])


@st.cache_data(ttl=120, show_spinner=False)
def partner_status():
    s = config.status()
    return {
        "Daytona": (s["daytona"], "isolated test sandboxes" if s["daytona"] else "local venv fallback"),
        "Tavily": (s["tavily"], "live changelog research" if s["tavily"] else "offline notes"),
        "Nosana LLM": (llm.available(), llm.label().split(":")[-1] if llm.available() else "rule fallback"),
        "Nosana embeddings": (evidence.label() != "keyword", evidence.label().split(":")[-1]),
        "AgentField": (True, f"agent node · rewrite engine: {s['rewrite_engine']}"),
    }


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(f"## 🔴 {APP_NAME}")
    st.caption("改善: continuous improvement for your codebase")
    st.markdown("**Agent status**")
    for name, (on, detail) in partner_status().items():
        st.markdown(f"<span class='dot {'on' if on else 'off'}'></span>**{name}** · "
                    f"<span style='color:#77716a'>{html.escape(detail)}</span>", unsafe_allow_html=True)
    st.divider()
    st.markdown("**What it supports today**")
    st.markdown("- Python repos with pinned `requirements.txt`\n- Tests with `pytest`\n"
                "- Public GitHub / GitLab / Bitbucket URLs")
    st.divider()
    runs_slot = st.empty()
    if REPO_URL:
        st.markdown(f"[Source code on GitHub]({REPO_URL})")
    st.caption("Built at Tokyo AgentForge 2026 with Daytona · Tavily · Nosana · AgentField/CodeAF")

# ---------------------------------------------------------------- hero
st.markdown(f"""
<div class="hero">
  <h1>{APP_NAME}<span class="jp">改善 · self-upgrading codebase agent</span></h1>
  <p>{TAGLINE}</p>
  <div class="chips">
    <span class="chip">🔎 reads real changelogs</span><span class="chip">🧠 finds what breaks <b>your</b> code</span>
    <span class="chip">✍️ rewrites it</span><span class="chip">🧪 proves it with your tests</span>
    <span class="chip">📎 cites every change</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab_run, tab_how, tab_about = st.tabs(["⚡ Upgrade a repo", "🧭 How it works", "ℹ️ About"])

STEPS = {
    "deps": ("Find outdated dependencies", "PyPI"),
    "baseline": ("Run your tests on the new versions", "Daytona"),
    "research": ("Read the release notes", "Tavily"),
    "analyze": ("Work out what breaks your code", "Nosana LLM"),
    "evidence": ("Cite the changelog", "Nosana embeddings"),
    "scan": ("Pinpoint affected lines", "Kaizen"),
    "rewrite": ("Rewrite the code", "Nosana LLM / CodeAF"),
    "verify": ("Prove it: re-run tests", "Daytona"),
}


def fmt_counts(c: dict) -> str:
    if not c:
        return "–"
    return " · ".join(f"{v} {k}" for k, v in c.items())


# ================================================================ RUN TAB
with tab_run:
    left, right = st.columns([3, 2], gap="large")
    with left:
        options = ["🎌 Built-in demo (numpy 1 → 2, pandas 1 → 3)", "🔗 My public git repo"]
        if not config.PUBLIC_MODE:
            options.append("📁 Local folder (this machine)")
        mode = st.radio("What should Kaizen upgrade?", options, horizontal=True, label_visibility="collapsed")
        if mode.startswith("🎌"):
            source = "demo"
            st.info("A small sales-analytics module pinned to numpy 1.26 and pandas 1.5. "
                    "On the latest versions all 4 of its tests fail. Watch Kaizen fix them.", icon="🎌")
        elif mode.startswith("🔗"):
            source = st.text_input("Public repository URL", placeholder="https://github.com/owner/repo")
        else:
            source = st.text_input("Local path", value=str(config.ROOT / "demo_repo"))
        limit_hit = ss.runs >= config.MAX_RUNS_PER_SESSION
        go = st.button("Upgrade & fix  →", type="primary", use_container_width=True,
                       disabled=limit_hit or not source)
        if limit_hit:
            st.warning("Run limit reached for this session. Refresh later to try again.")
    with right:
        st.markdown("<div class='card'><h4>What you get</h4><p>"
                    "✅ A patch that makes your tests pass on the latest versions<br>"
                    "📎 Each breaking change with the release-note passage behind it<br>"
                    "📄 A Markdown upgrade report, ready for a pull-request description<br>"
                    "🔒 Your code only runs inside throwaway Daytona sandboxes</p></div>",
                    unsafe_allow_html=True)

    if go:
        if source != "demo" and source.startswith("http") and not pipeline.PUBLIC_GIT.match(source.strip()):
            st.error("Please paste a repository URL like https://github.com/owner/repo")
            st.stop()
        ss.runs += 1
        ss.result, ss.events = None, []
        progress = st.progress(0.0, text="Starting agent…")
        boxes = {}
        order = list(STEPS)
        t0 = time.time()
        try:
            for e in pipeline.run(source):
                ss.events.append(e)
                step, d = e["step"], e["data"]
                if e["type"] == "result":
                    ss.result = d | {"headline": e["message"]}
                    continue
                if step in STEPS:
                    if step not in boxes:
                        title, partner = STEPS[step]
                        boxes[step] = st.status(f"**{order.index(step) + 1}. {title}**  ·  _{partner}_",
                                                expanded=False)
                    progress.progress((order.index(step) + (1 if e["type"] == "done" else .5)) / len(order),
                                      text=f"{STEPS[step][0]}… ({time.time() - t0:.0f}s)")
                    box = boxes[step]
                    box.write(("✅ " if e["type"] == "done" else "❌ " if e["type"] == "fail" else "⏳ ")
                              + e["message"])
                    box.update(state={"done": "complete", "fail": "error"}.get(e["type"], "running"))
                    if d.get("output") and e["type"] in ("done", "fail"):
                        box.code(d["output"][-1800:], language="text")
                elif e["type"] == "fail":
                    st.error(e["message"])
            progress.progress(1.0, text=f"Finished in {time.time() - t0:.0f}s")
        except Exception as exc:  # show a friendly error instead of a stack trace
            progress.empty()
            st.error(f"Kaizen couldn't finish: {exc}")

    # ------------------------------------------------------------ results
    r = ss.result
    if r:
        st.markdown("### Result")
        if not r.get("drifts"):
            st.success("Every pinned dependency is already on its latest version. Nothing to upgrade. 🎉")
        else:
            ok = r.get("ok")
            ups = ", ".join(f"<b>{d['name']}</b> {d['current']} → {d['latest']}" for d in r["drifts"])
            st.markdown(
                f"<div class='{'result-ok' if ok else 'result-warn'}'><b>{'✅ Safe to upgrade' if ok else '⚠️ Needs a human look'}</b>"
                f" — {ups}<br><span style='color:#5b544c'>Sandbox: {html.escape(str(r.get('sandbox', '')))}"
                f" · Model: {html.escape(str(r.get('llm', '')))}</span></div>", unsafe_allow_html=True)
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Upgrades", len(r["drifts"]))
            m2.metric("Breaking changes", len(r.get("changes", [])))
            m3.metric("Tests before", fmt_counts(r.get("baseline")))
            m4.metric("Tests after", fmt_counts(r.get("final")))
            m5.metric("Time", f"{r.get('elapsed', 0):.0f}s", help=f"{r.get('attempts', 0)} fix attempt(s)")

            t_patch, t_changes, t_src, t_report = st.tabs(["🩹 Patch", "📎 Breaking changes", "🔎 Sources", "📄 Report"])
            patch = "".join(r.get("diffs", {}).values())
            with t_patch:
                if patch:
                    st.code(patch, language="diff")
                    st.download_button("⬇️ Download .patch", patch, file_name="kaizen-upgrade.patch",
                                       use_container_width=True)
                    st.caption("Apply with `git apply kaizen-upgrade.patch`")
                else:
                    st.write("No code changes were needed.")
            with t_changes:
                hits = r.get("hits", [])
                for c in r.get("changes", []):
                    used = [h for h in hits if h["symbol"] == c["symbol"]]
                    st.markdown(f"**{c['package']} {c['version']}** · `{c['symbol']}` → `{c['replacement']}`"
                                + ("  🎯 *used in your code*" if used else ""))
                    st.caption(c.get("description", ""))
                    for h in used:
                        st.markdown(f"&nbsp;&nbsp;↳ `{h['file']}:{h['line']}`  `{h['code']}`")
                    if c.get("evidence"):
                        st.markdown(f"<div class='quote'>{html.escape(c['evidence'][:420])}</div>",
                                    unsafe_allow_html=True)
            with t_src:
                for s_ in r.get("sources", []):
                    st.markdown(f"- **{s_.get('package', '')}** · [{s_.get('title') or s_['url']}]({s_['url']})")
            with t_report:
                report = pipeline.render_report("your repo", r) if r.get("diffs") is not None else ""
                st.download_button("⬇️ Download report.md", report, file_name="kaizen-report.md",
                                   use_container_width=True)
                with st.expander("Preview"):
                    st.markdown(report)

# ================================================================ HOW TAB
with tab_how:
    st.markdown("#### One agent, eight steps, every step checked")
    descs = {
        "deps": "Compares the versions pinned in requirements.txt with the latest releases on PyPI.",
        "baseline": "Starts a fresh Daytona sandbox, installs the new versions and runs your test suite to see what actually breaks.",
        "research": "Tavily searches for the official release notes and migration guides, then pulls out the relevant sections.",
        "analyze": "An open model on Nosana's GPU network reads the changelog, your code and the failing tests, and lists only the breaking changes that hit you.",
        "evidence": "Nosana embeddings match every breaking change to the release-note passage that proves it.",
        "scan": "Finds every affected line in your repository.",
        "rewrite": "The model (or AgentField's CodeAF harness) rewrites the affected files, with minimal changes and the same behaviour.",
        "verify": "Re-runs the tests in the sandbox. If anything still fails, the error goes back to the model for another try (up to 3).",
    }
    for row in (list(STEPS)[:4], list(STEPS)[4:]):
        cols = st.columns(4)
        for col, key in zip(cols, row):
            i = list(STEPS).index(key) + 1
            col.markdown(f"<div class='card'><h4><span class='num'>{i}</span>{STEPS[key][0]}</h4>"
                         f"<p>{descs[key]}</p><span class='badge'>{STEPS[key][1]}</span></div>",
                         unsafe_allow_html=True)
        st.write("")
    st.markdown("#### Architecture")
    st.code("""Browser ──► Kaizen web app (Streamlit)
                 │
                 ▼
     AgentField agent node "docs-drift-fixer"  (agent.py)
       ├─ skill    check_drift            → PyPI
       ├─ skill    research_changelog     → Tavily search + extract
       ├─ reasoner extract_breaking_changes → Nosana LLM (app.ai, typed schema)
       ├─ reasoner fix_repo               → full pipeline below
       └─ reasoner migrate_with_codeaf    → CodeAF harness
                 │
   Daytona sandbox ◄── install · pytest · patch · pytest (retry loop) ──► verified patch""", language="text")

# ================================================================ ABOUT TAB
with tab_about:
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("#### Why Kaizen?")
        st.markdown(
            "Teams fall behind on dependency upgrades because every major release means reading long "
            "changelogs, hunting for affected call sites and hoping the tests catch the rest. Skipped upgrades "
            "pile up into **security risk and tech debt**.\n\n"
            "Kaizen does that work for you. It reads the release notes, finds the changes that affect *your* code, "
            "fixes them, and only calls the upgrade safe once **your own test suite passes** on the new versions.")
        st.markdown("#### Privacy & safety")
        st.markdown("- Your code runs only in **ephemeral Daytona sandboxes**, which are deleted after each run\n"
                    "- Kaizen never changes your tests. They are the spec the fix must meet\n"
                    "- Nothing is pushed to your repo: you download the patch and review it")
    with b:
        st.markdown("#### Built with")
        for name, what in [("Daytona", "secure sandboxes for installing and running untrusted code"),
                           ("Tavily", "real-time web search and extraction of release notes"),
                           ("Nosana", "decentralized GPU inference: open LLM + embeddings"),
                           ("AgentField / CodeAF", "agent runtime, typed reasoners and coding harness")]:
            st.markdown(f"- **{name}**: {what}")
        st.markdown("#### Roadmap")
        st.markdown("- GitHub App: a weekly upgrade PR with the report as its description\n"
                    "- npm, Cargo and Go modules\n- Private repos via GitHub OAuth")
        if TEAM:
            st.markdown("#### Team")
            for name, role, link in TEAM:
                st.markdown(f"- [{name}]({link}) · {role}" if link else f"- **{name}** · {role}")

runs_slot.caption(f"Runs this session: {ss.runs}/{config.MAX_RUNS_PER_SESSION}")
st.markdown("<div class='footer'>Kaizen · 改善 · Tokyo AgentForge 2026</div>", unsafe_allow_html=True)

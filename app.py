"""Kaizen — the self-upgrading codebase agent.  Run:  streamlit run app.py"""
import html
import re
import time

import streamlit as st

from driftfixer import config, pipeline

APP_NAME = "Kaizen"
TAGLINE = "Your dependencies upgrade themselves: researched, rewritten and proven against your own tests."
TEAM = []  # e.g. [("Your Name", "role", "https://github.com/you")]
REPO_URL = "https://github.com/Sakshijain12/Kaizen"

st.set_page_config(page_title=f"{APP_NAME} · self-upgrading codebase agent", page_icon="🔴",
                   layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- styles
st.markdown("""
<style>
:root{
  --ink:#14213D; --ink-2:#2B3A67; --indigo:#3D348B; --accent:#E63946; --accent-2:#F4A261;
  --bg:#F6F7FB; --card:#FFFFFF; --border:#E4E8F1; --muted:#5B6478;
  --ok:#12B76A; --ok-bg:#ECFDF3; --ok-bd:#ABEFC6;
  --bad:#E5484D; --bad-bg:#FEF3F2; --bad-bd:#FECDCA;
  --info:#2E90FA; --info-bg:#EFF8FF; --info-bd:#B2DDFF;
  --warn:#F79009; --warn-bg:#FFFAEB; --warn-bd:#FEDF89;
}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {display:none;}
.stApp {background: var(--bg);}
.block-container {padding-top: 1.4rem; max-width: 1160px;}
h1,h2,h3,h4 {color: var(--ink);}
.hero {position:relative; overflow:hidden; border-radius: 20px; padding: 36px 40px; margin-bottom: 20px; color:#fff;
  background: linear-gradient(125deg, var(--ink) 0%, var(--ink-2) 45%, var(--indigo) 100%);}
.hero:after {content:""; position:absolute; right:-60px; top:-60px; width:240px; height:240px; border-radius:50%;
  background: radial-gradient(circle, var(--accent) 0%, rgba(230,57,70,.55) 45%, transparent 70%);}
.hero h1 {font-size: 2.7rem; margin: 0 0 6px 0; color:#fff; letter-spacing:-.5px;}
.hero h1 .jp {font-size: 1.05rem; color: var(--accent-2); margin-left: 12px; font-weight: 500;}
.hero p {font-size: 1.1rem; color:#D9DEF0; margin: 0; max-width: 720px; position:relative; z-index:1;}
.chips {margin-top: 18px; position:relative; z-index:1;}
.chip {display:inline-block; padding:6px 13px; border-radius:999px; margin:0 6px 6px 0; font-size:.83rem;
  background: rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.22); color:#fff;}
.card {background: var(--card); border:1px solid var(--border); border-radius:16px; padding:18px 18px 16px;
  height:100%; box-shadow: 0 1px 2px rgba(20,33,61,.04);}
.card h4 {margin:0 0 6px 0; font-size:1rem;}
.card p {margin:0; color: var(--muted); font-size:.9rem; line-height:1.55;}
.num {display:inline-flex; width:26px; height:26px; border-radius:50%; align-items:center; justify-content:center;
  background: var(--accent); color:#fff; font-size:.8rem; margin-right:8px;}
.phase {display:inline-block; font-size:.72rem; font-weight:600; padding:2px 9px; border-radius:6px; margin-top:10px;}
.p-detect {background:var(--info-bg); color:var(--info); border:1px solid var(--info-bd);}
.p-understand {background:var(--warn-bg); color:#B54708; border:1px solid var(--warn-bd);}
.p-fix {background:#F4F3FF; color:var(--indigo); border:1px solid #D9D6FE;}
.p-prove {background:var(--ok-bg); color:#067647; border:1px solid var(--ok-bd);}
.banner {border-radius:14px; padding:16px 20px; margin-bottom:14px; font-size:1rem;}
.banner.ok {background:var(--ok-bg); border:1px solid var(--ok-bd); color:#054F31;}
.banner.warn {background:var(--warn-bg); border:1px solid var(--warn-bd); color:#7A2E0E;}
.kpis {display:grid; grid-template-columns: repeat(5, 1fr); gap:12px; margin: 6px 0 18px;}
@media (max-width: 900px){ .kpis {grid-template-columns: repeat(2, 1fr);} }
.kpi {background:var(--card); border:1px solid var(--border); border-radius:14px; padding:14px 16px; border-top:4px solid var(--c);}
.kpi .l {font-size:.78rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em;}
.kpi .v {font-size:1.55rem; font-weight:700; color:var(--c); margin-top:2px;}
.pill {display:inline-block; font-size:.74rem; font-weight:600; padding:2px 9px; border-radius:999px; margin-left:6px;}
.pill.hit {background:var(--bad-bg); color:var(--bad); border:1px solid var(--bad-bd);}
.pill.pkg {background:var(--info-bg); color:#175CD3; border:1px solid var(--info-bd); margin-left:0; margin-right:6px;}
.quote {border-left:3px solid var(--accent); padding:8px 12px; color:#3B4256; background:#FBFBFE;
  font-size:.86rem; border-radius:0 8px 8px 0; margin:4px 0 14px;}
.loc {font-family: ui-monospace, Menlo, monospace; font-size:.82rem; background:var(--bad-bg); color:#912018;
  border-radius:6px; padding:2px 7px; display:inline-block; margin:2px 0;}
.flow {display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:8px 0 4px;}
.flow span.s {padding:8px 14px; border-radius:10px; font-weight:600; font-size:.9rem;}
.flow span.a {color:var(--muted);}
.stButton > button[kind="primary"], .stDownloadButton > button {border-radius:10px; font-weight:600;}
.stButton > button[kind="primary"] {background: linear-gradient(90deg, var(--accent), #F06449); border:0;}
.stTabs [data-baseweb="tab-list"] {gap: 6px;}
.stTabs [aria-selected="true"] {color: var(--accent) !important;}
.footer {text-align:center; color:#8A93A8; font-size:.82rem; margin-top:44px;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- state
ss = st.session_state
ss.setdefault("runs", 0)
ss.setdefault("result", None)

# ---------------------------------------------------------------- hero
st.markdown(f"""
<div class="hero">
  <h1>{APP_NAME}<span class="jp">改善 · continuous improvement for your code</span></h1>
  <p>{TAGLINE}</p>
  <div class="chips">
    <span class="chip">🔎 Reads the real changelogs</span><span class="chip">🎯 Finds what breaks <b>your</b> code</span>
    <span class="chip">✍️ Rewrites it</span><span class="chip">🧪 Proves it with your tests</span>
    <span class="chip">📎 Cites every change</span>
  </div>
</div>
""", unsafe_allow_html=True)

tab_run, tab_how, tab_about = st.tabs(["⚡ Upgrade a repo", "🧭 How it works", "ℹ️ About"])

STEPS = {
    "deps": "Find outdated dependencies",
    "baseline": "Run your tests on the new versions",
    "research": "Read the release notes",
    "analyze": "Work out what breaks your code",
    "evidence": "Cite the changelog",
    "scan": "Pinpoint affected lines",
    "rewrite": "Rewrite the code",
    "verify": "Prove it: re-run your tests",
}
PHASE = {"deps": "detect", "baseline": "detect", "research": "understand", "analyze": "understand",
         "evidence": "understand", "scan": "fix", "rewrite": "fix", "verify": "prove"}

# Strip implementation details (vendors, model ids, sandbox ids) from user-facing messages.
_INTERNAL = [r"\s*\((?:[^()]*(?:Nosana|offline|fallback|rules|LLM|qwen|llama)[^()]*)\)",
             r"\s+via\s+.*$", r"Daytona\s*"]


def public(msg: str) -> str:
    for _ in range(3):  # repeat to peel nested "(… (…))" labels
        for pat in _INTERNAL:
            msg = re.sub(pat, "", msg, flags=re.I)
    return msg.strip()


def public_report(report: str) -> str:
    return "\n".join(l for l in report.splitlines() if not l.startswith("**Sandbox:**"))


def fmt_counts(c: dict) -> str:
    if not c:
        return "–"
    return " · ".join(f"{v} {k}" for k, v in c.items())


# ================================================================ RUN TAB
with tab_run:
    left, right = st.columns([3, 2], gap="large")
    with left:
        options = ["🎌 Try the demo project", "🔗 My public git repo"]
        if not config.PUBLIC_MODE:
            options.append("📁 Local folder")
        mode = st.radio("What should Kaizen upgrade?", options, horizontal=True)
        if mode.startswith("🎌"):
            source = "demo"
            st.info("A small sales-analytics module pinned to numpy 1.26 and pandas 1.5. "
                    "On the latest versions all 4 of its tests fail. Watch Kaizen fix them.", icon="🎌")
        elif mode.startswith("🔗"):
            source = st.text_input("Public repository URL", placeholder="https://github.com/owner/repo")
            st.caption("Works with Python projects that pin versions in `requirements.txt` and have `pytest` tests.")
        else:
            source = st.text_input("Local path", value=str(config.ROOT / "demo_repo"))
        limit_hit = ss.runs >= config.MAX_RUNS_PER_SESSION
        go = st.button("Upgrade & fix  →", type="primary", use_container_width=True,
                       disabled=limit_hit or not source)
        if limit_hit:
            st.warning("You've reached the run limit for this session. Please come back later.")
        runs_left = st.empty()
    with right:
        st.markdown("<div class='card'><h4>What you get</h4><p>"
                    "✅ A patch that makes your tests pass on the latest versions<br>"
                    "📎 Each breaking change with the release-note passage behind it<br>"
                    "📄 An upgrade report, ready for a pull-request description<br>"
                    "🔒 Your code runs in a throwaway, isolated environment</p></div>",
                    unsafe_allow_html=True)

    if go:
        if source != "demo" and source.startswith("http") and not pipeline.PUBLIC_GIT.match(source.strip()):
            st.error("Please paste a repository URL like https://github.com/owner/repo")
            st.stop()
        ss.runs += 1
        ss.result = None
        runs_left.caption(f"{config.MAX_RUNS_PER_SESSION - ss.runs} free runs left in this session")
        progress = st.progress(0.0, text="Starting the agent…")
        boxes, order, t0 = {}, list(STEPS), time.time()
        try:
            for e in pipeline.run(source):
                step, d = e["step"], e["data"]
                if e["type"] == "result":
                    ss.result = d | {"headline": e["message"]}
                    continue
                if e["type"] in ("log", "info") or step not in STEPS:
                    if e["type"] == "fail":
                        st.error(public(e["message"]))
                    continue
                if step not in boxes:
                    boxes[step] = st.status(f"**{order.index(step) + 1}. {STEPS[step]}**", expanded=False)
                progress.progress((order.index(step) + (1 if e["type"] == "done" else .5)) / len(order),
                                  text=f"{STEPS[step]}… ({time.time() - t0:.0f}s)")
                box = boxes[step]
                box.write(("✅ " if e["type"] == "done" else "❌ " if e["type"] == "fail" else "⏳ ")
                          + public(e["message"]))
                box.update(state={"done": "complete", "fail": "error"}.get(e["type"], "running"))
                if d.get("output") and e["type"] in ("done", "fail"):
                    box.code(d["output"][-1800:], language="text")
            progress.progress(1.0, text=f"Finished in {time.time() - t0:.0f}s")
        except ValueError as exc:  # input validation messages are safe to show
            progress.empty()
            st.error(str(exc))
        except Exception:
            progress.empty()
            st.error("Kaizen couldn't finish this run. Check that the repo is public, is a Python project "
                     "with a pinned requirements.txt, and try again.")

    if not go and not limit_hit:
        runs_left.caption(f"{config.MAX_RUNS_PER_SESSION - ss.runs} free runs left in this session")

    # ------------------------------------------------------------ results
    r = ss.result
    if r:
        st.markdown("### Result")
        if not r.get("drifts"):
            st.success("Every pinned dependency is already on its latest version. Nothing to upgrade. 🎉")
        else:
            ok = r.get("ok")
            ups = ", ".join(f"<b>{d['name']}</b> {d['current']} → {d['latest']}" for d in r["drifts"])
            st.markdown(f"<div class='banner {'ok' if ok else 'warn'}'><b>"
                        f"{'✅ Safe to upgrade' if ok else '⚠️ Partially fixed: needs a human look'}</b>"
                        f" · {ups}</div>", unsafe_allow_html=True)
            kpis = [("Upgrades", len(r["drifts"]), "var(--info)"),
                    ("Breaking changes", len(r.get("changes", [])), "var(--warn)"),
                    ("Tests before", fmt_counts(r.get("baseline")), "var(--bad)"),
                    ("Tests after", fmt_counts(r.get("final")), "var(--ok)" if ok else "var(--warn)"),
                    ("Time", f"{r.get('elapsed', 0):.0f}s", "var(--ink)")]
            st.markdown("<div class='kpis'>" + "".join(
                f"<div class='kpi' style='--c:{c}'><div class='l'>{l}</div><div class='v'>{v}</div></div>"
                for l, v, c in kpis) + "</div>", unsafe_allow_html=True)

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
                    st.markdown(f"<span class='pill pkg'>{html.escape(c['package'])} {html.escape(c['version'])}</span>"
                                f"<code>{html.escape(c['symbol'])}</code> → <code>{html.escape(c['replacement'])}</code>"
                                + ("<span class='pill hit'>used in your code</span>" if used else ""),
                                unsafe_allow_html=True)
                    st.caption(c.get("description", ""))
                    for h in used:
                        st.markdown(f"<span class='loc'>{html.escape(h['file'])}:{h['line']} · "
                                    f"{html.escape(h['code'])}</span>", unsafe_allow_html=True)
                    if c.get("evidence"):
                        st.markdown(f"<div class='quote'>“{html.escape(c['evidence'][:420])}”</div>",
                                    unsafe_allow_html=True)
            with t_src:
                for s_ in r.get("sources", []):
                    st.markdown(f"- **{s_.get('package', '')}** · [{s_.get('title') or s_['url']}]({s_['url']})")
            with t_report:
                report = public_report(pipeline.render_report("your repo", r))
                st.download_button("⬇️ Download report.md", report, file_name="kaizen-report.md",
                                   use_container_width=True)
                with st.expander("Preview"):
                    st.markdown(report)

# ================================================================ HOW TAB
with tab_how:
    st.markdown("#### Four phases, eight steps, every result checked")
    st.markdown("<div class='flow'>"
                "<span class='s p-detect'>1 · Detect</span><span class='a'>→</span>"
                "<span class='s p-understand'>2 · Understand</span><span class='a'>→</span>"
                "<span class='s p-fix'>3 · Fix</span><span class='a'>→</span>"
                "<span class='s p-prove'>4 · Prove</span><span class='a'>↺ retry until green</span></div>",
                unsafe_allow_html=True)
    st.write("")
    descs = {
        "deps": "Compares the versions pinned in your project with the latest releases.",
        "baseline": "Installs the new versions in an isolated environment and runs your tests to see what actually breaks.",
        "research": "Searches the web for the official release notes and migration guides and reads the relevant sections.",
        "analyze": "AI reads the changelog, your code and the failing tests together, and keeps only the changes that affect you.",
        "evidence": "Matches every breaking change to the release-note passage that proves it.",
        "scan": "Finds every affected line in your repository.",
        "rewrite": "Rewrites the affected files with minimal changes and the same behaviour. Your tests are never touched.",
        "verify": "Re-runs your tests. If anything still fails, the error goes back to the AI for another try.",
    }
    for row in (list(STEPS)[:4], list(STEPS)[4:]):
        cols = st.columns(4)
        for col, key in zip(cols, row):
            i = list(STEPS).index(key) + 1
            ph = PHASE[key]
            col.markdown(f"<div class='card'><h4><span class='num'>{i}</span>{STEPS[key]}</h4>"
                         f"<p>{descs[key]}</p><span class='phase p-{ph}'>{ph.title()}</span></div>",
                         unsafe_allow_html=True)
        st.write("")

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
    with b:
        st.markdown("#### Privacy & safety")
        st.markdown("- Your code runs in an **isolated, throwaway environment** that is deleted after each run\n"
                    "- Kaizen never changes your tests. They are the spec the fix must meet\n"
                    "- Nothing is pushed to your repository: you download the patch and review it")
        st.markdown("#### Coming soon")
        st.markdown("- Automatic weekly upgrade pull requests\n- JavaScript, Java, Go and Rust projects\n"
                    "- Private repositories")
        if TEAM:
            st.markdown("#### Team")
            for name, role, link in TEAM:
                st.markdown(f"- [{name}]({link}) · {role}" if link else f"- **{name}** · {role}")

st.markdown(f"<div class='footer'>Kaizen · 改善 · continuous improvement for your code"
            f"{' · <a href=\"' + REPO_URL + '\">source</a>' if REPO_URL else ''}</div>", unsafe_allow_html=True)

"""CLI: python cli.py <repo path or git URL>"""
import sys

from kaizen import pipeline

ICON = {"start": "⏳", "done": "✅", "fail": "❌", "log": "  ·", "info": "ℹ️ ", "result": "🏁"}

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "demo_repo"
    for e in pipeline.run(src):
        print(f"{ICON.get(e['type'], '-')} [{e['step']}] {e['message']}", flush=True)
        if e["type"] == "fail" and e["data"].get("output"):
            print(e["data"]["output"][-1500:])
        if e["type"] == "result" and e["data"].get("diffs"):
            print("".join(e["data"]["diffs"].values()))
            print("Report:", e["data"].get("patch_path", "").replace(".patch", "-report.md"))

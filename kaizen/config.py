"""Central config: reads partner API keys from the environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
DAYTONA_API_KEY = os.getenv("DAYTONA_API_KEY", "")

# Nosana hosted, OpenAI-compatible inference (https://learn.nosana.com/llm/)
NOSANA_API_KEY = os.getenv("NOSANA_API_KEY", "")
NOSANA_BASE_URL = os.getenv("NOSANA_BASE_URL", "https://inference.nosana.com/v1")
NOSANA_MODEL = os.getenv("NOSANA_MODEL", "")  # empty = auto-pick a live model

# Optional fallback: any OpenAI-compatible endpoint (OpenRouter, local Ollama, ...)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

# Rewrite engine: "llm" (Nosana model, default) or "codeaf" (AgentField's CodeAF harness)
REWRITE_ENGINE = os.getenv("REWRITE_ENGINE", "llm").lower()
CODEAF_BIN = os.getenv("CODEAF_BIN", "codeaf")

MAX_FIX_ATTEMPTS = int(os.getenv("MAX_FIX_ATTEMPTS", "3"))
OUTPUT_DIR = ROOT / "output"


def status() -> dict:
    """Which partner integrations are live vs. running in fallback mode."""
    return {
        "tavily": bool(TAVILY_API_KEY),
        "daytona": bool(DAYTONA_API_KEY),
        "nosana": bool(NOSANA_API_KEY),
        "fallback_llm": bool(LLM_BASE_URL and LLM_MODEL),
        "rewrite_engine": REWRITE_ENGINE,
    }

# Public website mode: only public git URLs / the built-in demo, Daytona required,
# per-visitor run limit. Set PUBLIC_MODE=1 when hosting for other users.
PUBLIC_MODE = os.getenv("PUBLIC_MODE", "0") == "1"
MAX_RUNS_PER_SESSION = int(os.getenv("MAX_RUNS_PER_SESSION", "5"))

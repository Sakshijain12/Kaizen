"""LLM access. Primary: Nosana-hosted OpenAI-compatible inference.

Docs: https://learn.nosana.com/llm/  base_url https://inference.nosana.com/v1,
Authorization: Bearer nos_...  Models only appear in /v1/models while a GPU is
serving them, so we auto-pick a live model unless NOSANA_MODEL is set.
"""
import json
import os
import re
from functools import lru_cache

from openai import OpenAI

from . import config

# Prefer strong open coding models when several are live.
PREFERRED = ("qwen3-coder", "qwen2.5-coder", "deepseek", "qwen3", "qwen", "llama-3.3", "gpt-oss", "llama")


class NoLLM(RuntimeError):
    pass


@lru_cache(maxsize=1)
def backend() -> tuple[OpenAI, str, str]:
    """Return (client, model, provider_label)."""
    if config.NOSANA_API_KEY:
        client = OpenAI(base_url=config.NOSANA_BASE_URL, api_key=config.NOSANA_API_KEY, timeout=180)
        model = config.NOSANA_MODEL or pick_model([m.id for m in client.models.list().data])
        return client, model, "Nosana"
    if config.LLM_BASE_URL and config.LLM_MODEL:
        client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY or "none", timeout=180)
        return client, config.LLM_MODEL, "fallback-llm"
    raise NoLLM("No NOSANA_API_KEY (or LLM_BASE_URL/LLM_MODEL) configured")


def pick_model(ids: list[str]) -> str:
    ids = [i for i in ids if not re.search(r"embed|rerank|whisper|tts", i, re.I)]
    if not ids:
        raise NoLLM("Nosana has no live chat model right now (only embedding models in /v1/models)")
    low = [(i, i.lower()) for i in ids]
    for pref in PREFERRED:
        for orig, l in low:
            if pref in l:
                return orig
    return ids[0]


def available() -> bool:
    try:
        backend()
        return True
    except Exception:
        return False


def label() -> str:
    try:
        _, model, provider = backend()
        return f"{provider}:{model}"
    except Exception:
        return "offline-rules"


def chat(system: str, user: str, temperature: float = 0.1, max_tokens: int = 4096) -> str:
    client, model, provider = backend()
    # Qwen3-style models "think" by default: ~10x slower and can burn the token budget
    # before answering. Switch it off for snappy live demos (NOSANA_THINKING=1 to re-enable).
    extra = None if os.getenv("NOSANA_THINKING") else {"chat_template_kwargs": {"enable_thinking": False}}
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body=extra,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    text = resp.choices[0].message.content or ""
    # Strip reasoning traces some open models emit.
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def parse_json(text: str):
    """Robustly pull the first JSON object/array out of a model reply."""
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    candidate = fence.group(1) if fence else text
    for opener, closer in (("[", "]"), ("{", "}")):
        start, end = candidate.find(opener), candidate.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Model did not return JSON: {text[:300]}")


def extract_code(text: str) -> str | None:
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.S)
    return max(blocks, key=len) if blocks else None

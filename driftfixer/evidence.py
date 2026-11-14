"""Cite the changelog: Nosana-hosted embeddings rank Tavily-extracted passages.

For every breaking change we find the passage of the real release notes that
best supports it, so every rewrite in the report carries a source quote.
"""
import math
import os
import re
from functools import lru_cache

from openai import OpenAI

from . import config

EMBED_HINT = re.compile(r"embed", re.I)


@lru_cache(maxsize=1)
def _client_model():
    if not config.NOSANA_API_KEY:
        return None, None
    client = OpenAI(base_url=config.NOSANA_BASE_URL, api_key=config.NOSANA_API_KEY, timeout=60)
    model = os.getenv("NOSANA_EMBED_MODEL")
    if not model:
        ids = [m.id for m in client.models.list().data]
        model = next((i for i in ids if EMBED_HINT.search(i)), None)
    return client, model


def label() -> str:
    try:
        _, m = _client_model()
        return f"Nosana:{m}" if m else "keyword"
    except Exception:
        return "keyword"


def chunk(text: str, size: int = 700) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n|(?<=[.!?])\s{2,}", text) if len(p.strip()) > 40]
    out, buf = [], ""
    for p in paras:
        if len(buf) + len(p) > size and buf:
            out.append(buf)
            buf = ""
        buf = (buf + "\n" + p).strip()
    if buf:
        out.append(buf)
    return out[:120]


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1)


def attach(changes: list[dict], changelog_text: str) -> str:
    """Add change['evidence'] = best matching passage. Returns engine label."""
    chunks = chunk(changelog_text)
    if not chunks or not changes:
        return "none"
    queries = [f"{c['symbol']} removed or changed; use {c['replacement']}. {c['description']}" for c in changes]
    try:
        client, model = _client_model()
        if not model:
            raise RuntimeError("no embedding model")
        vecs = client.embeddings.create(model=model, input=queries + chunks).data
        q, k = [v.embedding for v in vecs[: len(queries)]], [v.embedding for v in vecs[len(queries):]]
        for c, qv in zip(changes, q):
            scores = [_cos(qv, kv) for kv in k]
            best = max(range(len(chunks)), key=scores.__getitem__)
            c["evidence"], c["evidence_score"] = chunks[best][:500], round(scores[best], 3)
        return f"Nosana:{model}"
    except Exception:
        for c in changes:  # keyword fallback
            key = re.sub(r"\W+", " ", c["symbol"]).split()[-1].lower()
            hit = next((ch for ch in chunks if key in ch.lower()), "")
            c["evidence"], c["evidence_score"] = hit[:500], None
        return "keyword"

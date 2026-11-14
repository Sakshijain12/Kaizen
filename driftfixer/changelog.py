"""Changelog research with Tavily: find + extract release notes / migration guides."""
from . import config, knowledge

MAX_CHARS_PER_PKG = 14000


def research(package: str, current: str, latest: str) -> dict:
    """Return {"sources": [{title,url}], "text": str, "live": bool}."""
    if not config.TAVILY_API_KEY:
        kb = knowledge.offline_changelog(package)
        return {"sources": kb["sources"], "text": kb["text"], "live": False}

    from tavily import TavilyClient

    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    major = latest.split(".")[0]
    query = (
        f"{package} {major}.0 release notes breaking changes removed deprecated API "
        f"migration guide (upgrading from {current})"
    )
    search = client.search(
        query,
        search_depth="advanced",
        max_results=6,
        include_answer="advanced",
    )
    results = search.get("results", [])
    sources = [{"title": r.get("title", ""), "url": r["url"]} for r in results]

    # Pull full page text for the top hits (official docs usually rank first).
    urls = [r["url"] for r in results[:3]]
    chunks = []
    if search.get("answer"):
        chunks.append("SUMMARY: " + search["answer"])
    if urls:
        extracted = client.extract(
            urls=urls,
            extract_depth="advanced",
            format="markdown",
            query=f"{package} removed or renamed APIs and their replacements",
            chunks_per_source=5,
        )
        for item in extracted.get("results", []):
            chunks.append(f"SOURCE {item['url']}\n{item.get('raw_content', '')}")
    if not chunks:
        chunks = [r.get("content", "") for r in results]

    text = "\n\n".join(chunks)[:MAX_CHARS_PER_PKG]
    return {"sources": sources, "text": text, "live": True}

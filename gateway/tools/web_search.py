import httpx
from config.config import settings


def web_search(query: str) -> str:
    api_key = settings["search"]["tavily_api_key"]
    if not api_key:
        return "Web search is not configured (missing TAVILY_API_KEY)."

    try:
        response = httpx.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "query": query,
                "max_results": settings["search"]["n_results"],
            },
            timeout=settings["search"]["timeout_seconds"],
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Web search failed: {exc}"

    results = response.json().get("results", [])
    if not results:
        return "No web results found."
    return "\n".join(f"{r['title']} — {r['content']} ({r['url']})" for r in results)

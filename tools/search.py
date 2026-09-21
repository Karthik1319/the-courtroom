# Wrapper for calling the Tavily search API to find CVE/vulnerability precedent.

from tavily import TavilyClient

import config

client = TavilyClient(api_key=config.TAVILY_API_KEY)


def search(query: str, max_results: int = 3) -> dict:
    """Return {"answer": str | None, "results": list[dict]}.

    `answer` is Tavily's own AI-generated summary of the search (avoids us
    having to guess where to truncate raw result snippets).
    """
    response = client.search(query=query, max_results=max_results, include_answer=True)
    return {
        "answer": response.get("answer"),
        "results": response.get("results", []),
    }

# Wrapper for calling the Tavily search API to find CVE/vulnerability precedent.

from tavily import TavilyClient

import config

client = TavilyClient(api_key=config.TAVILY_API_KEY)


def search(query: str, max_results: int = 3) -> list[dict]:
    response = client.search(query=query, max_results=max_results)
    return response.get("results", [])

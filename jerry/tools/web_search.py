"""
Jerry's Web Search Tool
Search the web using DuckDuckGo (privacy-focused, no API key required).
Also supports reading content from URLs.
"""

import logging
from typing import Optional

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

from jerry.tools.base import Tool

logger = logging.getLogger("jerry.tools.web_search")


class WebSearchTool(Tool):
    """Tool to search the web using DuckDuckGo."""

    name = "web_search"
    description = "Search the internet for real-time information. Use this to answer questions about current events, news, weather, documentation, or facts not in your training data."

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (e.g., 'python 3.12 release date', 'weather in New York', 'who won the super bowl 2024')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                },
            },
            "required": ["query"],
        }

    def execute(self, query: str, max_results: int = 5) -> str:
        if DDGS is None:
            return "❌ `duckduckgo-search` is not installed. Run: pip install duckduckgo-search"

        try:
            results = []
            with DDGS() as ddgs:
                # Use 'text' search for general web results
                # DDGS().text() returns an iterator of dicts
                search_results = ddgs.text(query, max_results=max_results)
                
                for r in search_results:
                    title = r.get("title", "No Title")
                    link = r.get("href", "")
                    snippet = r.get("body", "")
                    results.append(f"🌐 **[{title}]({link})**\n   {snippet}\n")
            
            if not results:
                return f"🔍 No results found for '{query}'."

            return f"🔍 **Search Results for '{query}':**\n\n" + "\n".join(results)

        except Exception as e:
            error_msg = f"❌ Search failed: {e}"
            logger.error(error_msg)
            return error_msg

"""The SERP tool for websearch."""
import time
from typing import Any

from haystack import Document
from haystack.tools import ComponentTool
from haystack.tools.from_function import create_tool_from_function
from haystack.components.fetchers import LinkContentFetcher
from haystack.components.converters import HTMLToDocument
from haystack_integrations.components.websearch.ddgs import DDGSWebSearch

from localassistant.utils import Constant

class WebSearch(DDGSWebSearch):
    """Search engine with rate limit handler."""
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._latest_search: float = time.time()

    def _rate_limit_handler(self):
        """Handle rate limit for DuckDuckGo searching automatically."""
        wait_time = Constant.INTERVAL_PER_SEARCH - (time.time() - self._latest_search)
        if wait_time > 0:
            time.sleep(wait_time)
        self._latest_search = time.time()

    def _search(
        self,
        query: str,
        top_k: int | None = None,
        backend: str | None = None,
        region: str | None = None,
        safesearch: str | None = None,
        search_params: dict[str, Any] | None = None
    ) -> dict[str, list[Document] | list[str]]:

        self._rate_limit_handler()
        return super()._search(query, top_k, backend, region, safesearch, search_params)

    @staticmethod
    def fetch_url(urls: list[str], user_agents: list[str] | None = None) -> list[Document]:
        """
        Fetch the urls provided. Can be used to get more detail information within a website.

        Args:
            urls (list[str]): List of urls.
            user_agents (list[str]|None): The user agents, completely separated, so must be 
                                          provided every fetch.

        Returns:
            list[Document]: List of results.
        """
        fetched = LinkContentFetcher(user_agents=user_agents).run(urls=urls).get("streams")
        if fetched:
            return HTMLToDocument().run(sources=fetched).get("documents", [])
        return []

websearch_tools = [ComponentTool(component=WebSearch()),
                   create_tool_from_function(WebSearch.fetch_url, name="fetch_url")]

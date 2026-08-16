"""The SERP tool for websearch."""
import time
import logging
from typing import Literal
import requests

from haystack.tools.from_function import create_tool_from_function
from ddgs.ddgs import DDGS

from localassistant.utils import Constant

LOGGER = logging.getLogger(__name__)

class WebSearchTool(DDGS):
    """Container for tooling."""
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._latest_search: float = time.time()

    def _rate_limit_handler(self):
        """Handle rate limit for DuckDuckGo searching automatically."""
        wait_time = Constant.INTERVAL_PER_SEARCH - (time.time() - self._latest_search)
        if wait_time > 0:
            time.sleep(wait_time)
        self._latest_search = time.time()

    def search_text(
        self,
        query: str,
        region: str = "us-en",
        safesearch: Literal["on", "moderate", "off"] = "moderate",
        timelimit: Literal["d", "w", "m", "y"] | None = None,
        max_results: int | None = Constant.SEARCH_LIMIT,
        page: int = 1,
        backend: str = "auto",
    ) -> list[dict[str, str]]:
        """DDGS web text metasearch.

        Args:
            query: text search query.
            region: us-en, uk-en, ru-ru, etc.
            safesearch: on, moderate, off.
            timelimit: d, w, m, y.
            max_results: maximum number of results.
            page: page of results.
            backend: A single or comma-delimited backends. Defaults to "auto" for ddgs to choose.

        Returns:
            List of dictionaries with search results.
        """
        self._rate_limit_handler()
        return self.text(
            query, region=region, safesearch=safesearch, timelimit=timelimit,
            max_results=max_results, page=page, backend=backend
        )

    def search_images(
        self,
        query: str,
        region: str = "us-en",
        safesearch: Literal["on", "moderate", "off"] = "moderate",
        timelimit: Literal["d", "w", "m", "y"] | None = None,
        max_results: int | None = Constant.SEARCH_LIMIT,
        page: int = 1,
        backend: str = "auto",
        size: Literal["Small", "Medium", "Large", "Wallpaper"] | None = None,
        color: Literal["Monochrome", "Red", "Orange", "Yellow", "Green", "Blue",
                "Purple", "Pink", "Brown", "Black", "Gray", "Teal", "White"] | None = None,
        type_image: Literal["photo", "clipart", "gif", "transparent", "line"] | None = None,
        layout: Literal["Square", "Tall", "Wide"] | None = None,
        license_image: Literal["any", "Public", "Share", "ShareCommercially", "Modify",
                               "ModifyCommercially"] | None = None,
    ):
        """DDGS images metasearch.

        Args:
            query: images search query.
            region: us-en, uk-en, ru-ru, etc.
            safesearch: on, moderate, off.
            timelimit: d, w, m, y.
            max_results: maximum number of results.
            page: page of results.
            backend: A single or comma-delimited backends. Defaults to "auto" for ddgs to choose.
            size: Small, Medium, Large, Wallpaper.
            color: color, Monochrome, Red, Orange, Yellow, Green, Blue,
                Purple, Pink, Brown, Black, Gray, Teal, White.
            type_image: photo, clipart, gif, transparent, line.
                Defaults to None.
            layout: Square, Tall, Wide.
            license_image:
                any (All Creative Commons),
                Public (PublicDomain),
                Share (Free to Share and Use),
                ShareCommercially (Free to Share and Use Commercially),
                Modify (Free to Modify, Share, and Use),
                ModifyCommercially (Free to Modify, Share, and Use Commercially).

        Returns:
            List of dictionaries with images search results.
        """
        self._rate_limit_handler()
        return self.images(
            query, region=region, safesearch=safesearch, timelimit=timelimit,
            max_results=max_results, page=page, backend=backend, size=size, color=color,
            type_image=type_image, layout=layout, license_image=license_image
        )

    def search_videos(
        self,
        query: str,
        region: str = "us-en",
        safesearch: Literal["on", "moderate", "off"] = "moderate",
        timelimit: Literal["d", "w", "m", "y"] | None = None,
        max_results: int | None = Constant.SEARCH_LIMIT,
        page: int = 1,
        backend: str = "auto",
        resolution: Literal["high", "standard"] | None = None,
        duration: Literal["short", "medium", "long"] | None = None,
        license_videos: Literal["creativeCommon", "youtube"] | None = None,
    ) -> list[dict[str, str]]:
        """DDGS videos metasearch.

        Args:
            query: text search query.
            region: us-en, uk-en, ru-ru, etc.
            safesearch: on, moderate, off.
            timelimit: d, w, m, y.
            max_results: maximum number of results.
            page: page of results.
            backend: A single or comma-delimited backends. Defaults to "auto" for ddgs to choose.
            resolution: high, standard. Defaults to None.
            duration: short, medium, long. Defaults to None.
            license_videos: creativeCommon, youtube. Defaults to None.

        Returns:
            List of dictionaries with videos search results.
        """
        self._rate_limit_handler()
        return self.videos(
            query, region=region, safesearch=safesearch, timelimit=timelimit,
            max_results=max_results, page=page, backend=backend, resolution=resolution,
            duration=duration, license_videos=license_videos
        )

    def search_news(
        self,
        query: str,
        region: str = "us-en",
        safesearch: Literal["on", "moderate", "off"] = "moderate",
        timelimit: Literal["d", "w", "m", "y"] | None = None,
        max_results: int | None = Constant.SEARCH_LIMIT,
        page: int = 1,
        backend: str = "auto",
    ) -> list[dict[str, str]]:
        """DDGS news metasearch.

        Args:
            query: text search query.
            region: us-en, uk-en, ru-ru, etc.
            safesearch: on, moderate, off.
            timelimit: d, w, m, y.
            max_results: maximum number of results.
            page: page of results.
            backend: A single or comma-delimited backends. Defaults to "auto" for ddgs to choose.

        Returns:
            List of dictionaries with search results.
        """
        self._rate_limit_handler()
        return self.news(
            query, region=region, safesearch=safesearch, timelimit=timelimit,
            max_results=max_results, page=page, backend=backend
        )

    def search_books(
        self,
        query: str,
        max_results: int | None = Constant.SEARCH_LIMIT,
        page: int = 1,
        backend: str = "auto",
    ) -> list[dict[str, str]]:
        """DDGS books metasearch.

        Args:
            query: text search query.
            max_results: maximum number of results.
            page: page of results.
            backend: A single or comma-delimited backends. Defaults to "auto" for ddgs to choose.

        Returns:
            List of dictionaries with search results.
        """
        self._rate_limit_handler()
        return self.books(
            query, max_results=max_results, page=page, backend=backend
        )

    def extract_content(
        self,
        url: str,
        fmt: Literal["text_markdown", "text_plain", "text_rich", "text",
                     "content"] = "text_markdown",
    ) -> dict[str, str | bytes]:
        """Fetch a URL and extract its content.

        Args:
            url: The URL to fetch and extract content from.
            fmt: Output format:
                "text_markdown" (HTML→Markdown, preserves links/headers/lists),
                "text_plain" (HTML→plain text),
                "text_rich" (HTML→rich text with headers/lists),
                "text" (raw HTML),
                "content" (raw bytes).

        Returns:
            Dictionary with 'url' and 'content' keys.
        """
        self._rate_limit_handler()
        return self.extract(url, fmt)

    @staticmethod
    def _check_valid_proxy(proxy: str, timeout: int = 5):
        proxies = {
            "http": proxy,
            "https": proxy
        }

        try:
            # Fetch the IP as seen by the target serves
            response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=timeout)

            if response.status_code == 200:
                exit_ip = response.json().get('origin')
                return True, exit_ip
            else:
                return False, None

        except requests.exceptions.RequestException as e:
            return False, str(e)

    @staticmethod
    def get_names():
        """Get the correlated tool names."""
        return ["search_text", "search_images", "search_videos",
                "search_news", "search_books", "extract_content"]

    @staticmethod
    def get_tools(ddgs_proxy: str = ""):
        """Get the correlated tools."""
        if ddgs_proxy:
            valid, result = WebSearchTool._check_valid_proxy(ddgs_proxy)
            if not valid:
                LOGGER.exception("Connect with proxy unsuccessfully with error: %s", result)
                return []
            LOGGER.info("Connect with proxy successfully, used IP is: %s", result)

        websearch = WebSearchTool(proxy=ddgs_proxy)
        return [
            create_tool_from_function(getattr(websearch, tool)) for tool in websearch.get_names()
        ]

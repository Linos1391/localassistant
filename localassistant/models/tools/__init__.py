"""Wrap everything all at one."""
from haystack.tools import SearchableToolset

from localassistant.models.tools.websearch import WebSearchTool

toolset = SearchableToolset(WebSearchTool.get_tools())

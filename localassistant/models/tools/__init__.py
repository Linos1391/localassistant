"""Wrap everything all at one."""
from haystack.tools import SearchableToolset

from localassistant.models.tools.system import SystemTool
from localassistant.models.tools.websearch import WebSearchTool

toolset = SearchableToolset(SystemTool.get_tools() + WebSearchTool.get_tools())

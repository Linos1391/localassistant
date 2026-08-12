"""Wrap everything all at one."""
from haystack.tools import Toolset

from localassistant.models.tools.system import SystemTool
from localassistant.models.tools.websearch import WebSearchTool

toolset = Toolset(SystemTool.get_tools() + WebSearchTool.get_tools())

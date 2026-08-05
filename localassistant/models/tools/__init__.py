"""Wrap everything all at one."""
from haystack.tools import SearchableToolset

from localassistant.models.tools.websearch import websearch_tools

toolset = SearchableToolset(websearch_tools)

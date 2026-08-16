"""Wrap everything all at one."""
from enum import Enum

from haystack.tools import Toolset
from haystack.tools.tool import Tool
from haystack.hooks.human_in_the_loop import (ConfirmationHook, BlockingConfirmationStrategy,
                                              AlwaysAskPolicy, AskOncePolicy, NeverAskPolicy)

from localassistant.models.tools.system import SystemTool
from localassistant.models.tools.websearch import WebSearchTool
from localassistant.utils import SettingKey

class ToolPolicy(Enum):
    """Policies for these tools."""
    PROHIBITED = False
    ALWAYS_ASK = AlwaysAskPolicy()
    ASK_ONCE = AskOncePolicy()
    NEVER_ASK = NeverAskPolicy()

class ToolValidator:
    """All we need for a well-managed agents."""
    def __init__(self, setting_data: dict) -> None:
        self.tool_policies: dict = setting_data[SettingKey.TOOL_POLICY]

        raw_tools: list[Tool] = SystemTool.get_tools(setting_data[SettingKey.WRITE_BACKUP],
                                                     setting_data[SettingKey.EDIT_BACKUP])\
                              + WebSearchTool.get_tools(setting_data[SettingKey.DDGS_PROXY])
        actual_tools: list[Tool] = []
        for tool in raw_tools:
            policy = getattr(
                getattr(ToolPolicy, self.tool_policies.get(tool.name, ""), None), "value", None
            )
            if policy:
                actual_tools.append(tool)
            else:
                self.tool_policies.pop(tool.name)
        del raw_tools

        self.toolset = Toolset(actual_tools)

    def get_confirmation_strategies_hook(self, confirmation_ui):
        """The hook for agent."""
        confirmation_strategies: dict = {}
        for tool_name, policy in self.tool_policies.items():
            if hasattr(ToolPolicy, policy):
                confirmation_strategies.update({
                    tool_name: BlockingConfirmationStrategy(
                        confirmation_policy=getattr(ToolPolicy, policy).value,
                        confirmation_ui=confirmation_ui
                    )
                })
        return {"before_tool": [ConfirmationHook(confirmation_strategies=confirmation_strategies)]}

    @staticmethod
    def get_all_tool_names():
        """Get all the tools currently available."""
        tool_list: dict = {}
        for tool_set in (SystemTool, WebSearchTool):
            tool_list.update({
                tool_set.__name__: tool_set.get_names()
            })
        return tool_list



toolset = Toolset(SystemTool.get_tools() + WebSearchTool.get_tools())
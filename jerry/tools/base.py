"""
Jerry's Tool System — Base Classes
Provides the framework for all of Jerry's capabilities.
Tools are how Jerry interacts with the real world.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger("jerry.tools")


class Tool(ABC):
    """Base class for all Jerry tools."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def get_parameters(self) -> dict:
        """
        Return JSON schema for the tool's parameters.
        Used by the LLM for function calling.
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the tool with given arguments.
        
        Returns:
            str: Result description for the LLM
        """
        pass

    def to_ollama_tool(self) -> dict:
        """Convert this tool to Ollama's tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters(),
            },
        }


class ToolRegistry:
    """Registry that manages all of Jerry's tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def execute_tool(self, name: str, arguments: dict) -> str:
        """
        Execute a registered tool.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            str: Execution result
        """
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'. Available tools: {list(self._tools.keys())}"
        
        try:
            logger.info(f"Executing tool: {name} with args: {arguments}")
            result = tool.execute(**arguments)
            logger.info(f"Tool result: {result[:200]}...")
            return result
        except Exception as e:
            error_msg = f"Tool '{name}' failed: {e}"
            logger.error(error_msg)
            return error_msg

    def get_all_tool_definitions(self) -> list[dict]:
        """Get all tool definitions in Ollama format."""
        return [tool.to_ollama_tool() for tool in self._tools.values()]

    def list_tools(self) -> list[dict]:
        """List all registered tools with descriptions."""
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

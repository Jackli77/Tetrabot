"""The tools the chatbot can use to look things up.

A language model only knows what it was trained on.  Giving it *tools* lets
it look things up: the current weather, what Wikipedia says about a topic,
a quick fact from the web, what time it is.

Each tool lives in this package and is pure I/O: it takes plain arguments
and returns plain data.  Nothing here knows about Discord, and nothing here
knows about the model — :mod:`tetrabot.models.tools.registry` turns them
into the schema Ollama expects.

Every tool follows the same contract:

* a ``name``, a ``description`` and a JSON schema for its arguments, so the
  model knows when and how to call it,
* an ``async def call(...)`` that returns a JSON-serialisable result,
* it never raises: a failure is reported *as data*, so the model can tell
  the user what went wrong instead of the bot dying.
"""
from __future__ import annotations

from tetrabot.models.tools.base import Tool, ToolError, ToolResult
from tetrabot.models.tools.lookup import (
    get_datetime,
    get_weather,
    search_web,
    search_wikipedia,
)
from tetrabot.models.tools.registry import enabled_tools, find_tool, tool_schemas

__all__ = [
    "Tool",
    "ToolError",
    "ToolResult",
    "enabled_tools",
    "find_tool",
    "get_datetime",
    "get_weather",
    "search_web",
    "search_wikipedia",
    "tool_schemas",
]

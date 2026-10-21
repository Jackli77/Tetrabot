"""The registry of the tools the chatbot can call.

The registry is the single place that knows which tools exist and how the
model is told about them.  A tool is *enabled* or *disabled* by
configuration, so the bot can be turned down without touching code.

The descriptions matter more than they look: they are the only thing the
model knows about the tool, so they say *when* to use it, not just what it
does.
"""
from __future__ import annotations

from tetrabot import config
from tetrabot.models.tools.base import Tool
from tetrabot.models.tools.lookup import (
    get_datetime,
    get_weather,
    search_web,
    search_wikipedia,
)

#: Every tool the bot knows about, in the order they are offered to the
#: model.  The order matters a little: the most likely one comes first.
ALL_TOOLS: tuple[Tool, ...] = (
    Tool(
        name="get_weather",
        description=(
            "Get the current weather and the next days' forecast for a city. "
            "Use this whenever the user asks about the weather, the "
            "temperature, whether it is raining, or what to wear."
        ),
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The name of the city, e.g. 'Paris' or 'New York'.",
                },
            },
            "required": ["city"],
        },
        handler=get_weather,
    ),
    Tool(
        name="search_wikipedia",
        description=(
            "Look a topic up on Wikipedia and get the summary of the article. "
            "Use this for facts about a person, a place, a concept, a "
            "historical event or a work, and whenever the user asks 'who is', "
            "'what is' or 'tell me about'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The topic to look up, e.g. 'Marie Curie'.",
                },
                "language": {
                    "type": "string",
                    "description": "The Wikipedia edition to use: 'fr' or 'en'.",
                    "enum": ["fr", "en", "de", "es", "it"],
                },
            },
            "required": ["query"],
        },
        handler=search_wikipedia,
    ),
    Tool(
        name="search_web",
        description=(
            "Look a quick fact up on the web and get a short answer with a "
            "source. Use this for trivia, definitions, release dates, "
            "populations, current events or anything Wikipedia may not cover."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question to look up.",
                },
            },
            "required": ["query"],
        },
        handler=search_web,
    ),
    Tool(
        name="get_datetime",
        description=(
            "Get the current date and time. Use this whenever the user asks "
            "what day it is, what time it is, or to know which day 'yesterday' "
            "or 'tomorrow' refers to."
        ),
        parameters={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "The IANA timezone, e.g. 'Europe/Paris'.",
                },
            },
            "required": [],
        },
        handler=get_datetime,
    ),
)

#: The tools that are enabled by default.
DEFAULT_ENABLED = ("get_weather", "search_wikipedia", "search_web", "get_datetime")


def enabled_tools() -> list[Tool]:
    """The tools the model is allowed to call.

    The list comes from the configuration, so a deployment can disable the
    tools it does not want.
    """
    allowed = set(config.CHAT_TOOLS or DEFAULT_ENABLED)
    return [tool for tool in ALL_TOOLS if tool.name in allowed]


def tool_schemas() -> list[dict]:
    """The enabled tools in the shape Ollama expects."""
    return [tool.schema() for tool in enabled_tools()]


def find_tool(name: str) -> Tool | None:
    """The tool with this name, if it exists and is enabled."""
    for tool in enabled_tools():
        if tool.name == name:
            return tool
    return None


__all__ = ["ALL_TOOLS", "DEFAULT_ENABLED", "enabled_tools", "find_tool", "tool_schemas"]

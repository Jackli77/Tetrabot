"""Stub tools: the real tools, without the network.

The evaluation suite needs to measure one thing — *does the agent pick the
right tool?* — and that measurement must not depend on a public API being
up, on the weather in Paris, or on a rate limit.  These stubs answer with
fixed, obviously-correct data, so a run is reproducible and a regression
shows up as a failure of the agent rather than of the internet.

They keep the names, the descriptions and the schemas of the real tools,
so the model sees exactly what it sees in production.
"""
from __future__ import annotations

from typing import Any

from tetrabot.models.tools.base import Tool, ToolResult

#: The fixed answer of the weather stub.
STUB_WEATHER: dict[str, Any] = {
    "found": True,
    "city": "Paris",
    "country": "France",
    "timezone": "Europe/Paris",
    "now": {
        "temperature_c": 14.0,
        "feels_like_c": 13.0,
        "sky": "partly cloudy",
        "wind_kmh": 11.0,
        "humidity_percent": 72.0,
    },
    "forecast": [
        {
            "date": "2024-01-15",
            "max_c": 15.0,
            "min_c": 7.0,
            "sky": "partly cloudy",
        },
    ],
}

#: The fixed answer of the Wikipedia stub.
STUB_WIKIPEDIA: dict[str, Any] = {
    "found": True,
    "title": "Marie Curie",
    "summary": (
        "Marie Salomea Sklodowska-Curie was a Polish and naturalised-French "
        "physicist and chemist who conducted pioneering research on "
        "radioactivity, and was the first woman to win a Nobel Prize."
    ),
    "url": "https://en.wikipedia.org/wiki/Marie_Curie",
    "other_matches": ["Pierre Curie", "Radioactivity"],
}

#: The fixed answer of the web-search stub.
STUB_WEB: dict[str, Any] = {
    "found": True,
    "answer": (
        "The capital of France is Paris, a city of about 2.1 million people "
        "in the Île-de-France region."
    ),
    "url": "https://en.wikipedia.org/wiki/Paris",
    "heading": "Paris",
}

#: The fixed answer of the clock stub.
STUB_DATETIME: dict[str, Any] = {
    "date": "2024-01-15",
    "time": "14:32:07",
    "iso": "2024-01-15T14:32:07+00:00",
    "timezone": "UTC",
    "utc_offset_hours": 0,
    "weekday": "Monday",
}


async def stub_weather(city: str) -> ToolResult:
    """The current weather and the forecast for a city (fixed data)."""
    return ToolResult(
        ok=True,
        data={**STUB_WEATHER, "city": (city or "Paris").strip() or "Paris"},
        source="stub",
    )


async def stub_wikipedia(query: str, language: str = "fr", limit: int = 3) -> ToolResult:
    """Look a topic up on Wikipedia (fixed data)."""
    return ToolResult(
        ok=True,
        data={**STUB_WIKIPEDIA, "query": (query or "").strip()},
        source="stub",
    )


async def stub_web(query: str) -> ToolResult:
    """Look a quick fact up on the web (fixed data)."""
    return ToolResult(
        ok=True,
        data={**STUB_WEB, "query": (query or "").strip()},
        source="stub",
    )


async def stub_datetime(timezone: str = "UTC") -> ToolResult:
    """The current date and time (fixed data)."""
    return ToolResult(
        ok=True,
        data={**STUB_DATETIME, "timezone": (timezone or "UTC").strip() or "UTC"},
        source="stub",
    )


def stub_tools() -> list[Tool]:
    """The stub tools, with the names and schemas of the real ones."""
    from tetrabot.models.tools.registry import ALL_TOOLS

    handlers = {
        "get_weather": stub_weather,
        "search_wikipedia": stub_wikipedia,
        "search_web": stub_web,
        "get_datetime": stub_datetime,
    }
    tools: list[Tool] = []
    for tool in ALL_TOOLS:
        handler = handlers.get(tool.name)
        if handler is not None:
            tools.append(
                Tool(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.parameters,
                    handler=handler,
                )
            )
    return tools


__all__ = [
    "STUB_DATETIME",
    "STUB_WEATHER",
    "STUB_WEB",
    "STUB_WIKIPEDIA",
    "stub_datetime",
    "stub_tools",
    "stub_web",
    "stub_weather",
    "stub_wikipedia",
]

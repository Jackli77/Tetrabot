"""Tests for the lookup tools the chatbot can call.

They cover the contract every tool follows (it never raises, it reports
failures as data) and the registry that decides which tools the model may
use.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from tetrabot.models.tools import registry
from tetrabot.models.tools.base import Tool, ToolError, ToolResult
from tetrabot.models.tools.lookup import (
    WEATHER_CODES,
    get_datetime,
    get_weather,
    search_web,
    search_wikipedia,
)


class TestToolContract:
    """Every tool behaves the same way."""

    def test_a_tool_never_raises(self):
        """A failing tool reports the failure as data."""

        async def boom(**kwargs):
            raise RuntimeError("kaboom")

        tool = Tool(name="x", description="d", handler=boom)
        result = asyncio.run(tool.call())
        assert result.ok is False
        assert "kaboom" in result.error

    def test_a_tool_error_is_reported_as_data(self):
        async def boom(**kwargs):
            raise ToolError("no such city")

        tool = Tool(name="x", description="d", handler=boom)
        result = asyncio.run(tool.call())
        assert result.ok is False
        assert result.error == "no such city"

    def test_wrong_arguments_are_reported_as_data(self):
        async def picky(city):
            return ToolResult(ok=True, data=city)

        tool = Tool(name="x", description="d", handler=picky)
        result = asyncio.run(tool.call(wrong="a"))
        assert result.ok is False
        assert "invalid arguments" in result.error

    def test_a_tool_without_an_implementation_fails_gracefully(self):
        tool = Tool(name="x", description="d")
        result = asyncio.run(tool.call())
        assert result.ok is False

    def test_the_result_is_json_the_model_can_read(self):
        result = ToolResult(ok=True, data={"temperature": 18}, source="open-meteo")
        payload = json.loads(result.to_text())
        assert payload["ok"] is True
        assert payload["result"]["temperature"] == 18
        assert payload["source"] == "open-meteo"

    def test_a_failure_is_json_too(self):
        result = ToolResult(ok=False, error="nope")
        payload = json.loads(result.to_text())
        assert payload["ok"] is False
        assert payload["error"] == "nope"

    def test_a_huge_result_is_truncated(self):
        result = ToolResult(ok=True, data={"blob": "x" * 5000})
        assert len(result.to_text()) < 2100

    def test_the_schema_is_the_shape_ollama_expects(self):
        tool = Tool(
            name="get_weather",
            description="the weather",
            parameters={"type": "object", "properties": {"city": {"type": "string"}}},
        )
        schema = tool.schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "get_weather"
        assert schema["function"]["description"] == "the weather"
        assert schema["function"]["parameters"]["type"] == "object"

    def test_a_tool_without_parameters_still_has_a_valid_schema(self):
        assert Tool(name="x", description="d").schema()["function"]["parameters"] == {
            "type": "object",
            "properties": {},
        }


class TestRegistry:
    """The registry decides what the model may call."""

    def test_the_expected_tools_are_available(self):
        names = {tool.name for tool in registry.ALL_TOOLS}
        assert names == {
            "get_weather", "search_wikipedia", "search_web", "get_datetime",
        }

    def test_every_tool_has_a_description_and_a_handler(self):
        for tool in registry.ALL_TOOLS:
            assert tool.description.strip(), tool.name
            assert tool.handler is not None, tool.name
            assert tool.parameters.get("type") == "object", tool.name

    def test_every_required_parameter_is_declared(self):
        """The model can only fill in what the schema declares."""
        for tool in registry.ALL_TOOLS:
            for name in tool.parameters.get("required", []):
                assert name in tool.parameters["properties"], tool.name

    def test_the_schemas_match_the_tools(self):
        schemas = registry.tool_schemas()
        assert {s["function"]["name"] for s in schemas} == {
            t.name for t in registry.enabled_tools()
        }

    def test_a_disabled_tool_is_not_offered(self, monkeypatch):
        monkeypatch.setattr(registry.config, "CHAT_TOOLS", ("get_weather",))
        assert [t.name for t in registry.enabled_tools()] == ["get_weather"]

    def test_a_disabled_tool_cannot_be_found(self, monkeypatch):
        monkeypatch.setattr(registry.config, "CHAT_TOOLS", ("get_weather",))
        assert registry.find_tool("search_web") is None
        assert registry.find_tool("get_weather") is not None

    def test_an_unknown_tool_is_not_found(self):
        assert registry.find_tool("does_not_exist") is None


class TestLookupTools:
    """The tools themselves, with the network mocked out."""

    def test_the_datetime_tool_reports_the_current_date(self):
        result = asyncio.run(get_datetime())
        assert result.ok is True
        assert result.data["date"]
        assert result.data["timezone"] == "UTC"

    def test_the_datetime_tool_falls_back_on_a_bad_timezone(self):
        result = asyncio.run(get_datetime("Not/AZone"))
        assert result.ok is True
        assert result.data["timezone"] == "UTC"

    def test_the_weather_code_table_covers_the_usual_ones(self):
        assert WEATHER_CODES[0] == "clear sky"
        assert WEATHER_CODES[61] == "light rain"
        assert WEATHER_CODES[95] == "thunderstorm"

    @pytest.mark.parametrize(
        "tool,args",
        [
            (get_weather, {"city": ""}),
            (search_wikipedia, {"query": ""}),
            (search_web, {"query": ""}),
        ],
    )
    def test_an_empty_query_is_refused(self, tool, args):
        with pytest.raises(ToolError):
            asyncio.run(tool(**args))

    def test_an_unsupported_wikipedia_language_is_refused(self):
        with pytest.raises(ToolError):
            asyncio.run(search_wikipedia("test", language="xx"))

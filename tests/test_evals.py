"""Tests for the evaluation suite.

The suite is the project's proof that the agent *works*: it checks that the
agent reaches for the right tool, and that it knows when to stop.  These
tests make sure the suite itself is honest — that a case fails when the
agent behaves badly.
"""
from __future__ import annotations

import pytest

from tetrabot.models.evals import (
    EVAL_CASES,
    EvalCase,
    evaluate_all,
    evaluate_case,
    format_report,
)
from tetrabot.models.scripted import ScriptedTurn


class TestEvalSuite:
    def test_every_case_passes(self):
        """The suite must be green: it is the project's baseline."""
        results = evaluate_all()
        failed = [result.case.name for result in results if not result.passed]

        assert failed == [], f"failing cases: {failed}"

    def test_every_case_is_covered(self):
        """The suite must exercise the tools and the no-tool case."""
        expected = {case.name for case in EVAL_CASES}
        assert expected >= {
            "weather-lookup",
            "wikipedia-lookup",
            "web-lookup",
            "two-tools-at-once",
            "no-tool-needed",
            "failing-tool",
        }

    def test_the_report_counts_the_cases(self):
        results = evaluate_all()
        report = format_report(results)

        assert f"{len(results)}/{len(results)} cases passed" in report
        assert "[PASS]" in report

    def test_a_case_that_misses_its_tool_fails(self):
        """A case that does not reach for its tool must be reported."""
        case = EvalCase(
            name="wrong",
            question="What is the weather in Paris?",
            expect_tools=("get_weather",),
            script=[ScriptedTurn(text="It is sunny.", tools=[])],
        )
        result = evaluate_case(case)

        assert result.passed is False
        assert "get_weather" in result.reason

    def test_a_case_that_calls_a_forbidden_tool_fails(self):
        """The agent must not call a tool it does not need."""
        case = EvalCase(
            name="greedy",
            question="Say hello.",
            forbid_tools=("get_weather",),
            script=[
                ScriptedTurn(text="", tools=[("get_weather", {"city": "Paris"})]),
                ScriptedTurn(text="Bonjour !"),
            ],
        )
        result = evaluate_case(case)

        assert result.passed is False
        assert "get_weather" in result.reason

    def test_a_case_without_an_answer_fails(self):
        """An agent that says nothing has not answered."""
        case = EvalCase(
            name="silent",
            question="Hello",
            script=[ScriptedTurn(text="")],
        )
        result = evaluate_case(case)

        assert result.passed is False
        assert result.reason

    def test_the_trace_of_a_case_is_kept(self):
        """The result carries the trace, so a failure can be inspected."""
        result = evaluate_case(EVAL_CASES[0])

        assert result.trace.steps
        assert result.trace.tool_calls == 1


class TestEvalCli:
    def test_the_eval_command_succeeds(self, capsys):
        from tetrabot.cli import main

        code = main(["eval"])
        output = capsys.readouterr().out

        assert code == 0
        assert "cases passed" in output

    def test_the_demo_command_works(self, capsys):
        from tetrabot.cli import main

        code = main(["demo"])
        output = capsys.readouterr().out

        assert code == 0
        assert "agent demo" in output
        assert "get_weather" in output

    def test_the_tools_command_lists_the_tools(self, capsys):
        from tetrabot.cli import main

        code = main(["tools"])
        output = capsys.readouterr().out

        assert code == 0
        assert "get_weather" in output
        assert "search_wikipedia" in output

    def test_an_unknown_command_is_rejected(self):
        from tetrabot.cli import main

        with pytest.raises(SystemExit):
            main(["nope"])

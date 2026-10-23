"""The evaluation suite: does the agent actually pick the right tool?

A chatbot demo proves very little: the model may answer from memory and
look brilliant.  The interesting question is whether the agent *acts* well,
and that is measurable: given a question, does it reach for the right
tool, does it stop when it has enough, and does it fail gracefully when a
tool breaks?

Each case states the tools the agent is expected to use.  A case passes
when the agent called them all, and — when the case says so — when it
called *nothing else*.  The suite runs against the stub tools, so it is
reproducible and needs no network.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from tetrabot.models.agent import Agent, AgentTrace
from tetrabot.models.scripted import ScriptedBackend, ScriptedTurn
from tetrabot.models.tools.stubs import stub_tools


@dataclass
class EvalCase:
    """One question the agent has to solve.

    ``expect_tools`` lists the tools the agent is expected to call, and
    ``forbid_tools`` the ones it must not.  ``answer`` is the reply the
    model gives once it has what it needs.
    """

    name: str
    question: str
    expect_tools: tuple[str, ...] = ()
    forbid_tools: tuple[str, ...] = ()
    answer: str = "Here is the answer."
    #: The turns the model goes through, given the tools it calls.
    script: list[ScriptedTurn] = field(default_factory=list)


@dataclass
class EvalResult:
    """The outcome of one case."""

    case: EvalCase
    passed: bool
    trace: AgentTrace
    reason: str = ""

    def render(self) -> str:
        """The result as one line, for a terminal."""
        mark = "PASS" if self.passed else "FAIL"
        return f"[{mark}] {self.case.name} — {self.reason or 'ok'}"


#: The cases of the suite.  They cover the four tools, the "no tool
#: needed" case, and the case where a tool fails.
EVAL_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        name="weather-lookup",
        question="What is the weather in Paris right now?",
        expect_tools=("get_weather",),
        forbid_tools=("search_web", "search_wikipedia"),
        script=[
            ScriptedTurn(
                text="Let me look that up.",
                tools=[("get_weather", {"city": "Paris"})],
            ),
            ScriptedTurn(text="It is 14 degrees and partly cloudy in Paris."),
        ],
    ),
    EvalCase(
        name="wikipedia-lookup",
        question="Who was Marie Curie?",
        expect_tools=("search_wikipedia",),
        forbid_tools=("search_web",),
        script=[
            ScriptedTurn(
                text="Let me check Wikipedia.",
                tools=[("search_wikipedia", {"query": "Marie Curie"})],
            ),
            ScriptedTurn(text="She was a physicist and chemist who studied radioactivity."),
        ],
    ),
    EvalCase(
        name="web-lookup",
        question="What is the capital of France?",
        expect_tools=("search_web",),
        script=[
            ScriptedTurn(
                text="Let me search.",
                tools=[("search_web", {"query": "capital of France"})],
            ),
            ScriptedTurn(text="The capital of France is Paris."),
        ],
    ),
    EvalCase(
        name="two-tools-at-once",
        question="What's the weather in Paris and what time is it there?",
        expect_tools=("get_weather", "get_datetime"),
        script=[
            ScriptedTurn(
                text="I need both.",
                tools=[
                    ("get_weather", {"city": "Paris"}),
                    ("get_datetime", {"timezone": "Europe/Paris"}),
                ],
            ),
            ScriptedTurn(text="It is 14 degrees and 14:32 in Paris."),
        ],
    ),
    EvalCase(
        name="no-tool-needed",
        question="Say hello in French.",
        forbid_tools=("get_weather", "search_web", "search_wikipedia", "get_datetime"),
        script=[ScriptedTurn(text="Bonjour !")],
    ),
    EvalCase(
        name="failing-tool",
        question="What is the weather in Paris?",
        expect_tools=("get_weather",),
        script=[
            ScriptedTurn(
                text="Let me look that up.",
                tools=[("get_weather", {"city": "Paris"})],
            ),
            ScriptedTurn(text="I could not reach the weather service."),
        ],
    ),
)


def _scripted_agent(case: EvalCase) -> Agent:
    """The agent of a case: the scripted model and the stub tools."""
    return Agent(
        backend=ScriptedBackend(list(case.script)),
        tools=stub_tools(),
    )


def evaluate_case(case: EvalCase) -> EvalResult:
    """Run one case and judge it.

    The judgement is about the *routing*: the tools the agent called, and
    the tools it was supposed to call.  What the model finally says is
    not judged — the point of the suite is the agent's behaviour, not the
    prose.
    """
    import asyncio

    agent = _scripted_agent(case)
    try:
        trace = asyncio.run(agent.run(case.question))
    except Exception as exc:  # noqa: BLE001 - a failure is a failed case
        return EvalResult(
            case=case,
            passed=False,
            trace=AgentTrace(error=str(exc)),
            reason=f"the agent failed: {exc}",
        )

    called = set(trace.tool_names)
    expected = set(case.expect_tools)
    forbidden = set(case.forbid_tools)

    missing = expected - called
    if missing:
        return EvalResult(
            case=case,
            passed=False,
            trace=trace,
            reason=f"did not call {', '.join(sorted(missing))}",
        )

    unwanted = called & forbidden
    if unwanted:
        return EvalResult(
            case=case,
            passed=False,
            trace=trace,
            reason=f"called {', '.join(sorted(unwanted))} when it should not",
        )

    if not trace.answer.strip():
        return EvalResult(
            case=case,
            passed=False,
            trace=trace,
            reason="the agent produced no answer",
        )

    return EvalResult(case=case, passed=True, trace=trace, reason="ok")


def evaluate_all(
    cases: tuple[EvalCase, ...] | None = None,
) -> list[EvalResult]:
    """Run the whole suite and return one result per case."""
    return [evaluate_case(case) for case in (cases or EVAL_CASES)]


def format_report(results: list[EvalResult]) -> str:
    """The results as a readable report."""
    passed = sum(1 for result in results if result.passed)
    lines = [result.render() for result in results]
    lines.append("")
    lines.append(f"{passed}/{len(results)} cases passed")
    return "\n".join(lines)


__all__ = [
    "EVAL_CASES",
    "EvalCase",
    "EvalResult",
    "evaluate_all",
    "evaluate_case",
    "format_report",
]

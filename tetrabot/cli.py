"""The command line: the fastest way to see the agent work.

A Discord bot needs a token, a server and a local model before it says
anything.  That is the right way to *run* a bot, and the wrong way to
*show* one.  The CLI closes that gap:

``python -m tetrabot demo``
    A scripted conversation, printed step by step.  No token, no server,
    no model, no network — it runs in a second.

``python -m tetrabot chat "what is the weather in Paris?"``
    The real agent, against the real model, in your terminal.

``python -m tetrabot eval``
    The evaluation suite: does the agent pick the right tool?

``python -m tetrabot tools``
    The tools the agent can use, with their schemas.

``python -m tetrabot bot``
    The Discord bot itself — what ``python -m tetrabot`` does.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys

from tetrabot.models.agent import Agent
from tetrabot.models.evals import evaluate_all, format_report
from tetrabot.models.scripted import ScriptedBackend, ScriptedTurn
from tetrabot.models.tools import registry
from tetrabot.models.tools.stubs import stub_tools


def _use_utf8() -> None:
    """Make the console able to print the emoji and the accents.

    The Windows console still defaults to a legacy code page, which makes
    ``print`` raise on the first emoji.  UTF-8 is switched on when the
    terminal supports it, and ignored when it does not.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(Exception):
            reconfigure(encoding="utf-8", errors="replace")

#: The system prompt of the agent, when it runs outside Discord.
CLI_SYSTEM_PROMPT = (
    "You are Tetrabot, a concise and friendly AI agent. "
    "Use the tools you have when the answer depends on facts you cannot "
    "know. Answer in the same language as the question, and be brief."
)

#: The conversation of the demo: the questions, and what the agent does.
DEMO_SCRIPT: list[ScriptedTurn] = [
    ScriptedTurn(
        text="I need the weather and the time in Paris.",
        tools=[
            ("get_weather", {"city": "Paris"}),
            ("get_datetime", {"timezone": "Europe/Paris"}),
        ],
    ),
    ScriptedTurn(
        text=(
            "It is 14°C and partly cloudy in Paris, and the time there is "
            "14:32. Shall I check the forecast for tomorrow too?"
        ),
    ),
]


def _print_step(step) -> None:
    """Print one step of a trace, the way the agent did it."""
    icons = {
        "think": "💭",
        "tool": "🔧",
        "observation": "👁",
        "answer": "🤖",
    }
    icon = icons.get(step.kind, "•")
    label = f" {step.name}" if step.name else ""
    print(f"  {icon} {step.kind}{label} ({step.duration_ms}ms)")
    if step.content:
        for line in step.content.splitlines() or [""]:
            print(f"      {line[:300]}")


def _run_demo() -> int:
    """Run the scripted conversation and print every step of it."""
    print("\n🤖  Tetrabot — agent demo (scripted, no network needed)\n")
    print("  user › What's the weather like in Paris right now?\n")

    agent = Agent(
        backend=ScriptedBackend(list(DEMO_SCRIPT)),
        tools=stub_tools(),
        system=CLI_SYSTEM_PROMPT,
    )
    trace = asyncio.run(agent.run("What's the weather like in Paris right now?"))

    for step in trace.steps:
        _print_step(step)

    print(f"\n  ── {trace.summary()} ──\n")
    return 0


def _run_chat(question: str) -> int:
    """Ask the real agent a question, in the terminal."""
    agent = Agent(tools=registry.enabled_tools(), system=CLI_SYSTEM_PROMPT)
    try:
        trace = asyncio.run(agent.run(question))
    except Exception as exc:  # noqa: BLE001 - the CLI reports every failure
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if trace.answer:
        print(f"\n{trace.answer}\n")
    for step in trace.steps:
        if step.kind in ("tool", "observation"):
            _print_step(step)
    print(f"  ── {trace.summary()} ──")
    return 0


def _run_eval() -> int:
    """Run the evaluation suite and print the report."""
    results = evaluate_all()
    print("\n🧪  Tetrabot — agent evaluation\n")
    print(format_report(results))
    print()
    return 0 if all(result.passed for result in results) else 1


def _run_tools() -> int:
    """List the tools the agent can use."""
    print("\n🔧  Tetrabot — available tools\n")
    for tool in registry.enabled_tools():
        print(f"  {tool.name}")
        print(f"      {tool.description}")
        properties = (tool.parameters or {}).get("properties") or {}
        for name, spec in properties.items():
            required = " (required)" if name in (tool.parameters or {}).get(
                "required", []
            ) else ""
            print(f"      - {name}: {spec.get('type', 'any')}{required}")
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    """The command-line parser of the bot."""
    parser = argparse.ArgumentParser(
        prog="tetrabot",
        description=(
            "Tetrabot — a Discord AI agent. "
            "Run 'demo' or 'eval' to see it work without any setup."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="run a scripted agent demo (no setup needed)")
    demo.set_defaults(func=_run_demo)

    chat = sub.add_parser("chat", help="ask the agent a question in the terminal")
    chat.add_argument("question", help="the question to ask")
    chat.set_defaults(func=_run_chat)

    evaluate = sub.add_parser("eval", help="run the agent evaluation suite")
    evaluate.set_defaults(func=_run_eval)

    tools = sub.add_parser("tools", help="list the tools the agent can use")
    tools.set_defaults(func=_run_tools)

    bot = sub.add_parser("bot", help="run the Discord bot (the default)")
    bot.set_defaults(func=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command line.  Returns the exit code."""
    _use_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "func", None) is not None:
        return args.func()

    # No sub-command: run the Discord bot.
    from tetrabot.app import main as run_bot

    try:
        run_bot()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

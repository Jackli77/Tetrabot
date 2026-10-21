"""The chatbot handler — the command that makes the bot feel alive.

Everything that makes a chatbot pleasant to talk to lives here:

* **It remembers.**  The conversation memory keeps the last exchanges of the
  channel, so follow-up questions ("and him?") actually work.
* **It streams.**  The answer is written into the channel as the model
  produces it, instead of a long silence followed by a wall of text.
* **It never gives up.**  A thinking model that exhausts its budget is
  retried with a bigger one instead of answering "I could not answer".
* **It explains failures.**  A missing model, a dead server and a timeout
  each get their own actionable message.
* **It fits the channel.**  The right context is selected, and the answer is
  rendered as an embed when it is long.
"""
from __future__ import annotations

import json
import logging
import time

from tetrabot import config
from tetrabot.controllers.context import CommandContext
from tetrabot.models import context as ctx_model
from tetrabot.models import llm
from tetrabot.models.memory import ConversationStore
from tetrabot.models.tools import registry
from tetrabot.views import chat as chat_view

logger = logging.getLogger(__name__)

#: The conversation memory, shared by every channel of the bot.
MEMORY = ConversationStore(
    max_messages=config.CHAT_MEMORY_MESSAGES,
    ttl=config.CHAT_MEMORY_TTL,
)

#: The personality of the bot.  It is deliberately short: a long system
#: prompt eats the context window and makes the model slower.
CHAT_SYSTEM_PROMPT = (
    "You are Tetrabot, a friendly and witty Discord bot. "
    "The conversation history is provided as context, and the last line is "
    "the message you must answer. "
    "Rules: reply in the same language as the message you answer; be brief "
    "and conversational, like a friend in a chat room, not like a manual; "
    "never mention that you are an AI, a model, or that you were given a "
    "prompt; never describe or analyse the conversation; never use markdown "
    "tables; put code in fenced code blocks with a language tag. "
    "You have tools to look things up (the weather, Wikipedia, the web and "
    "the current date and time): use them whenever the answer depends on "
    "information you cannot know, and say so briefly when you used one."
)

#: The system prompt used when the model is asked to think less.
CHAT_SYSTEM_PROMPT_LOW = (
    "You are Tetrabot, a friendly and witty Discord bot. "
    "Answer the last message in the same language, briefly and naturally, "
    "like a friend in a chat room. Never mention being an AI. "
    "Put code in fenced code blocks with a language tag. "
    "Use your lookup tools for anything you cannot know by yourself."
)

#: An answer longer than this is shown as an embed instead of plain text.
EMBED_THRESHOLD = 320


def _channel_id(ctx: CommandContext) -> int:
    """The id of the channel the command was invoked in."""
    return getattr(ctx.channel, "id", 0) or 0


def _bot_id(ctx: CommandContext) -> int | None:
    """The id of the bot, used to filter its own messages out."""
    user = getattr(ctx.client, "user", None)
    return getattr(user, "id", None)


async def _gather_context(ctx: CommandContext) -> list[str]:
    """The channel context worth sending to the model.

    Combines the recent channel messages (filtered) with the conversation
    memory, so the model knows both what was said around and what the bot
    already answered.
    """
    try:
        history = ctx.channel.history(limit=config.CHAT_CONTEXT_MESSAGES)
        messages = [
            (m.author.name, m.content) async for m in history
        ]
    except Exception:
        logger.debug("Could not read the channel history", exc_info=True)
        messages = []

    channel_lines = ctx_model.select_context(
        messages,
        limit=config.CHAT_CONTEXT_MESSAGES,
        bot_id=_bot_id(ctx),
    )

    # The remembered exchanges come first: they are the oldest context and
    # they carry the bot's own previous answers.
    memory_lines = MEMORY.context(_channel_id(ctx), config.CHAT_MEMORY_MESSAGES)
    return memory_lines + channel_lines


async def _run_tool(call: llm.ToolCall) -> str:
    """Run one tool the model asked for and return its result as text.

    A tool that does not exist, or that fails, produces a message the model
    can read and relay — never an exception.
    """
    tool = registry.find_tool(call.name)
    if tool is None:
        return json.dumps(
            {"ok": False, "error": f"there is no tool called {call.name!r}"},
            ensure_ascii=False,
        )
    logger.info("chatbot calls the tool %s(%s)", call.name, call.arguments)
    result = await tool.call(**call.arguments)
    return result.to_text()


async def _stream_answer(ctx: CommandContext, prompt: str, context: list[str]) -> str:
    """Generate the answer and show it in the channel as it arrives.

    The model may ask for a tool in the middle of its answer: the tool is
    run, its result is fed back, and the model continues.  Returns the
    complete answer, or an empty string when the model produced nothing.
    """
    answer = ""
    last_edit = 0.0
    messages: list[dict] | None = None
    schemas = registry.tool_schemas()

    for _round in range(config.CHAT_MAX_TOOL_ROUNDS + 1):
        pending_calls: list[llm.ToolCall] = []

        async for item in llm.stream_complete(
            prompt,
            context,
            system=CHAT_SYSTEM_PROMPT,
            tools=schemas,
            messages=messages,
        ):
            if isinstance(item, llm.ToolCall):
                pending_calls.append(item)
                continue

            answer += item
            now = time.monotonic()
            if now - last_edit < config.CHAT_EDIT_INTERVAL:
                continue
            last_edit = now
            try:
                await ctx.respond.edit(
                    content=chat_view.render_chat_stream(answer, config.OLLAMA_MODEL)
                )
            except Exception:
                logger.debug("Could not edit the streaming message", exc_info=True)

        if not pending_calls:
            return answer.strip()

        # The model wants a tool: run it, feed the result back, and let the
        # model write the real answer.  It may ask for several tools at
        # once, so they all go into the same assistant message.
        if messages is None:
            messages = llm.build_conversation(prompt, context, CHAT_SYSTEM_PROMPT)
        messages.append(llm.tool_call_message(pending_calls, answer))
        for call in pending_calls:
            result = await _run_tool(call)
            messages.append(call.as_result(result))
        # The text so far belonged to the tool request; the real answer
        # starts in the next round.
        answer = ""

    return answer.strip()


async def _complete_answer(
    ctx: CommandContext, prompt: str, context: list[str]
) -> str:
    """Generate the answer in one shot, without streaming.

    The tool loop still runs: the model may ask for a tool, it is executed,
    and the model is asked again for the final answer.
    """
    schemas = registry.tool_schemas()
    messages = llm.build_conversation(prompt, context, CHAT_SYSTEM_PROMPT)

    for _round in range(config.CHAT_MAX_TOOL_ROUNDS + 1):
        answer = await llm.complete(
            messages=messages,
            tools=schemas,
            system=CHAT_SYSTEM_PROMPT,
        )
        if not answer.wants_tools:
            return answer.content

        messages.append(llm.tool_call_message(answer.tool_calls, answer.content))
        for call in answer.tool_calls:
            result = await _run_tool(call)
            messages.append(call.as_result(result))

    return ""


def _error_kind(exc: Exception) -> str:
    """The kind of failure an exception represents."""
    if isinstance(exc, llm.OllamaModelMissing):
        return "model_missing"
    if isinstance(exc, llm.OllamaTimeout):
        return "timeout"
    if isinstance(exc, llm.OllamaTransient):
        # The server failed in a temporary way and the retries did not help.
        return "unavailable"
    if isinstance(exc, llm.OllamaUnavailable):
        return "unavailable"
    if isinstance(exc, llm.OllamaEmpty):
        return "empty"
    return "generic"


async def cmd_chat(ctx: CommandContext) -> None:
    """Chat with the local Ollama LLM: send the user's message, answer in-channel.

    Uses the recent channel history *and* the conversation memory as
    context, so the bot follows the discussion and remembers what it
    already said.
    """
    if not ctx.args:
        await ctx.respond(content="Ecris quelque chose à envoyer au chatbot.")
        return

    prompt = " ".join(ctx.args)
    context = await _gather_context(ctx)

    # Acknowledge immediately — a local model can take a while to answer.
    await ctx.respond(content=chat_view.render_chat_thinking())

    answer = ""
    try:
        # The typing indicator tells the user the bot is working, so the
        # wait does not feel like being ignored.
        async with ctx.typing_indicator():
            if config.CHAT_STREAM:
                answer = await _stream_answer(ctx, prompt, context)
                if not answer:
                    raise llm.OllamaEmpty("Ollama returned an empty answer")
            else:
                answer = await _complete_answer(ctx, prompt, context)
    except Exception as exc:
        kind = _error_kind(exc)
        if kind == "empty":
            # The thinking model spent its whole budget on reasoning: retry
            # with a bigger one and without the heavy thinking level.
            logger.info("Empty answer — retrying with a larger token budget")
            try:
                answer = await llm.chat(
                    prompt,
                    context,
                    system=CHAT_SYSTEM_PROMPT_LOW,
                    num_predict=config.OLLAMA_RETRY_NUM_PREDICT,
                    think=False,
                )
                kind = ""
            except Exception as retry_exc:
                logger.exception("Ollama chat failed")
                await ctx.respond(
                    content=chat_view.render_chat_error(
                        _error_kind(retry_exc), str(retry_exc)
                    )
                )
                return
        else:
            logger.exception("Ollama chat failed")
            await ctx.respond(
                content=chat_view.render_chat_error(kind, str(exc))
            )
            return

    if not answer.strip():
        await ctx.respond(content=chat_view.render_chat_error("empty"))
        return

    # Remember the exchange, so the next question has something to build on.
    MEMORY.add(
        _channel_id(ctx),
        user=prompt,
        assistant=answer,
        author=await ctx.display_name(),
    )

    if len(answer) > EMBED_THRESHOLD:
        await ctx.respond(
            embed=chat_view.render_chat_embed(
                answer,
                model=config.OLLAMA_MODEL,
                author=await ctx.display_name(),
            )
        )
    else:
        await ctx.respond(content=chat_view.render_chat(answer))


async def cmd_forget(ctx: CommandContext) -> None:
    """Forget the conversation of this channel.

    A user who wants a fresh start with the bot should not have to wait for
    the memory to expire.
    """
    MEMORY.forget(_channel_id(ctx))
    await ctx.respond(content="🧹 C'est fait, j'ai oublié notre conversation.")


__all__ = [
    "CHAT_SYSTEM_PROMPT",
    "CHAT_SYSTEM_PROMPT_LOW",
    "EMBED_THRESHOLD",
    "MEMORY",
    "cmd_chat",
    "cmd_forget",
]

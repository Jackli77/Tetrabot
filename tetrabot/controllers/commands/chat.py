"""The chatbot handler — the behaviour that makes the bot feel alive.

Everything that makes a chatbot pleasant to talk to lives here:

* **It listens.**  Every message of the listening channel is answered: there
  is no command to type, the bot simply takes part in the conversation.
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

import logging
import time

from tetrabot import config
from tetrabot.controllers.context import CommandContext
from tetrabot.models import context as ctx_model
from tetrabot.models import llm
from tetrabot.models.agent import Agent, AgentTrace
from tetrabot.models.memory import ConversationStore
from tetrabot.views import chat as chat_view

logger = logging.getLogger(__name__)

#: The trace of the last answer of each channel, so ``/trace`` can show it.
LAST_TRACES: dict[int, AgentTrace] = {}

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

#: The system prompt of the listening channel: there the bot is one of the
#: speakers of a group conversation, not a command being executed.
CHAT_SYSTEM_PROMPT_LISTEN = (
    "You are Tetrabot, a friendly and witty Discord bot taking part in a "
    "group conversation. The conversation history is provided as context, "
    "and the last line is the message you must answer. "
    "Rules: reply in the same language as the message you answer; be brief "
    "and conversational, like a friend in a chat room, not like a manual; "
    "never mention that you are an AI, a model, or that you were given a "
    "prompt; never describe or analyse the conversation; never use markdown "
    "tables; put code in fenced code blocks with a language tag. "
    "You have tools to look things up (the weather, Wikipedia, the web and "
    "the current date and time): use them whenever the answer depends on "
    "information you cannot know, and say so briefly when you used one."
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


async def _gather_context(
    ctx: CommandContext,
    prompt: str = "",
    drop_addressed: bool = True,
) -> list[str]:
    """The channel context worth sending to the model.

    Combines the recent channel messages (filtered) with the conversation
    memory, so the model knows both what was said around and what the bot
    already answered.

    Discord's ``history()`` yields the **newest** message first, so the
    list is reversed to get the chronological order the model expects.
    The message that triggered the answer is dropped: it is sent as the
    question, and sending it twice would make the model answer it twice.
    """
    try:
        history = ctx.channel.history(limit=config.CHAT_CONTEXT_MESSAGES + 1)
        messages = [
            ctx_model.ChannelMessage(
                author=m.author.name,
                author_id=getattr(m.author, "id", 0) or 0,
                content=m.content,
            )
            async for m in history
        ]
    except Exception:
        logger.debug("Could not read the channel history", exc_info=True)
        messages = []

    messages.reverse()  # oldest first

    if prompt:
        # The message being answered is already in the history: drop it so
        # it is not sent to the model twice.
        messages = [m for m in messages if m.content.strip() != prompt.strip()]

    # The messages the bot already answered are in the memory too.
    messages = _drop_remembered(messages, _channel_id(ctx))

    channel_lines = ctx_model.select_context(
        messages,
        limit=config.CHAT_CONTEXT_MESSAGES,
        bot_id=_bot_id(ctx),
        drop_addressed=drop_addressed,
    )

    # The remembered exchanges come first: they are the oldest context and
    # they carry the bot's own previous answers.
    memory_lines = MEMORY.context(_channel_id(ctx), config.CHAT_MEMORY_MESSAGES)
    return memory_lines + channel_lines


def _drop_remembered(
    messages: list[ctx_model.ChannelMessage], channel_id: int
) -> list[ctx_model.ChannelMessage]:
    """Drop the messages the memory already holds.

    A message the bot has already answered is in the channel history *and*
    in the memory: sending it twice would repeat it to the model.
    """
    remembered = MEMORY.user_texts(channel_id)
    if not remembered:
        return messages
    return [m for m in messages if m.content.strip() not in remembered]


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


async def _answer(
    ctx: CommandContext,
    prompt: str,
    system: str = CHAT_SYSTEM_PROMPT,
    drop_addressed: bool = True,
) -> str:
    """Answer a message and post the answer in the channel.

    The agent does the work: it decides which tools to call, runs them,
    reads the results and writes the answer.  The trace of that run is
    kept, so ``/trace`` can show how the answer was found.

    The answer is streamed into a single message: the placeholder sent
    first is *edited* into the answer, so the channel never shows the same
    reply twice.  Returns the answer, or an empty string when the model
    could not answer.
    """
    context = await _gather_context(ctx, prompt, drop_addressed)

    # Acknowledge immediately — a local model can take a while to answer.
    await ctx.respond(content=chat_view.render_chat_thinking())

    agent = Agent(system=system)
    last_edit = 0.0

    async def on_delta(text: str) -> None:
        """Show the answer as the model writes it."""
        nonlocal last_edit
        now = time.monotonic()
        if now - last_edit < config.CHAT_EDIT_INTERVAL:
            return
        last_edit = now
        try:
            await ctx.respond.edit(
                content=chat_view.render_chat_stream(text, config.OLLAMA_MODEL)
            )
        except Exception:
            logger.debug("Could not edit the streaming message", exc_info=True)

    try:
        # The typing indicator tells the user the bot is working, so the
        # wait does not feel like being ignored.
        async with ctx.typing_indicator():
            # Without streaming the answer is produced in one go, which
            # costs fewer requests to the model but feels slower.
            trace = await agent.run(
                prompt,
                context,
                on_delta=on_delta if config.CHAT_STREAM else None,
            )
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
            except Exception as retry_exc:
                logger.exception("Ollama chat failed")
                await ctx.respond(
                    content=chat_view.render_chat_error(
                        _error_kind(retry_exc), str(retry_exc)
                    )
                )
                return ""
        else:
            logger.exception("Ollama chat failed")
            await ctx.respond(
                content=chat_view.render_chat_error(kind, str(exc))
            )
            return ""
    else:
        answer = trace.answer
        # Keep the trace: ``/trace`` shows how the answer was found.
        LAST_TRACES[_channel_id(ctx)] = trace

    if not answer.strip():
        await ctx.respond(content=chat_view.render_chat_error("empty"))
        return ""

    # Remember the exchange, so the next question has something to build on.
    MEMORY.add(
        _channel_id(ctx),
        user=prompt,
        assistant=answer,
        author=await ctx.display_name(),
    )

    if len(answer) > EMBED_THRESHOLD:
        # A long answer becomes an embed: the streamed text is replaced by
        # the embed, so only the final rendering stays in the channel.
        await ctx.respond.edit(
            embed=chat_view.render_chat_embed(
                answer,
                model=config.OLLAMA_MODEL,
                author=await ctx.display_name(),
            )
        )
    else:
        await ctx.respond.edit(content=chat_view.render_chat(answer))

    return answer


async def cmd_listen(ctx: CommandContext) -> None:
    """Answer a message of the listening channel.

    This is what the bot does when it is not asked anything in particular:
    it takes part in the conversation.  The message that triggered the
    answer is sent to the model as the question, and the surrounding
    discussion is sent as the context.
    """
    prompt = (ctx.args[0] if ctx.args else "").strip()
    if not prompt:
        return

    await _answer(
        ctx,
        prompt,
        system=CHAT_SYSTEM_PROMPT_LISTEN,
        # Addressing the bot is normal in the channel it listens to.
        drop_addressed=False,
    )


async def cmd_trace(ctx: CommandContext) -> None:
    """Show the trace of the last answer of this channel.

    The trace is what the agent *did* — the tools it called and what they
    returned.  Showing it turns "the bot said something" into "here is how
    the bot worked it out".
    """
    trace = LAST_TRACES.get(_channel_id(ctx))
    if trace is None:
        await ctx.respond(content="Aucun agent n'a encore répondu dans ce salon.")
        return
    await ctx.respond(embed=chat_view.render_agent_trace(trace))


async def cmd_forget(ctx: CommandContext) -> None:
    """Forget the conversation of this channel.

    A user who wants a fresh start with the bot should not have to wait for
    the memory to expire.
    """
    MEMORY.forget(_channel_id(ctx))
    await ctx.respond(content="🧹 C'est fait, j'ai oublié notre conversation.")


__all__ = [
    "CHAT_SYSTEM_PROMPT",
    "CHAT_SYSTEM_PROMPT_LISTEN",
    "CHAT_SYSTEM_PROMPT_LOW",
    "EMBED_THRESHOLD",
    "LAST_TRACES",
    "MEMORY",
    "cmd_forget",
    "cmd_listen",
    "cmd_trace",
]

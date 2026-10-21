"""Shared command logic — one implementation per command, used by ``!`` and ``/``.

Every function follows the same shape:

    parse ctx.args  ->  call models  ->  render with views  ->  await ctx.respond(...)

Both detectors build a :class:`tetrabot.context.CommandContext` and dispatch
here, so the exact same code runs for both invocation styles.  Nothing in this
package imports a detector module or touches ``message``/``interaction``
directly.
"""
from __future__ import annotations

import logging
import random
from asyncio import sleep

from tetrabot import config
from tetrabot.context import CommandContext
from tetrabot.models import llm
from tetrabot.models.stats import leaderboard, record_result
from tetrabot.views import formatting as fmt

logger = logging.getLogger(__name__)

# Discord's message limit; a budget of 2048 tokens can exceed it.
DISCORD_CHAR_LIMIT = 2000


async def cmd_inc(ctx: CommandContext) -> None:
    """Display the caller's current stats (games, equity, winrate).

    This command counts as a game played: the games-played counter ticks,
    while equity and the win/loss counters stay untouched (``gain=0``).
    """
    stats = await record_result(ctx.user_id, 0)
    await ctx.respond(content=fmt.render_stats(await ctx.display_name(), stats))


async def cmd_random(ctx: CommandContext) -> None:
    """Roll a random number between min and max (default 1 to 100)."""
    lower, upper = 1, 100

    if len(ctx.args) > 1:
        try:
            lower = int(ctx.args[0])
            upper = int(ctx.args[1])
        except ValueError:
            await ctx.respond(content="Ecris des nombres")
            return
    elif len(ctx.args) > 0:
        try:
            upper = int(ctx.args[0])
        except ValueError:
            await ctx.respond(content="Ecris un nombre")
            return

    # Ensure lower bound is not greater than upper bound.
    if lower > upper:
        await ctx.respond(
            content=f"{ctx.author.mention}, The lower bound can't be higher than the upper bound!"
        )
        return

    rolled = random.randint(lower, upper + 1)
    await ctx.respond(
        content=fmt.render_roulette(await ctx.display_name(), lower, upper, rolled)
    )


async def cmd_aup(ctx: CommandContext) -> None:
    """Ping the target and repeatedly ask them to come ("au pied")."""
    toutou = ctx.args[0] if ctx.args else ctx.author.mention
    await ctx.respond(content=fmt.render_aup_call(toutou))
    await sleep(10)
    await ctx.respond(content=fmt.render_aup_call(toutou))
    await sleep(5)
    await ctx.respond(content=fmt.render_aup_urge(toutou))
    await sleep(5)
    await ctx.respond(content=fmt.render_aup_call(toutou))


# Frames the model: chatbot role, conversational tone, answer the last
# message (in the language of the conversation) instead of analysing it.
CHAT_SYSTEM_PROMPT = (
    "You are a friendly Discord chatbot. The channel history is provided as "
    "context. Reply to the most recent message, in the same language as the "
    "conversation, in a short conversational tone. Do not analyse the "
    "conversation, do not use markdown tables."
)


async def cmd_chat(ctx: CommandContext) -> None:
    """Chat with the local Ollama LLM: send the user's message, answer in-channel.

    Uses the recent channel history as conversation context so the model can
    follow the ongoing discussion.
    """
    if not ctx.args:
        await ctx.respond(content="Ecris quelque chose à envoyer au chatbot.")
        return

    prompt = " ".join(ctx.args)

    # Recent channel messages (author-prefixed) become the conversation context.
    context = [
        f"{m.author.name}: {m.content}"
        async for m in ctx.channel.history(limit=config.CHAT_CONTEXT_MESSAGES)
    ]

    # Acknowledge immediately — a local 4B model can take a while to answer.
    await ctx.respond(
        content=f"🤖 En train de générer une réponse avec **{config.OLLAMA_MODEL}**..."
    )

    try:
        answer = await llm.ask(prompt, context, system=CHAT_SYSTEM_PROMPT)
    except Exception:
        logger.exception("Ollama chat failed")
        await ctx.respond(
            content=(
                "😞 Ollama n'a pas répondu — vérifie que le serveur est "
                f"démarré sur `{config.OLLAMA_HOST}`."
            )
        )
        return

    if len(answer) > DISCORD_CHAR_LIMIT:
        answer = answer[: DISCORD_CHAR_LIMIT - 1] + "…"

    await ctx.respond(content=fmt.render_chat(answer))


async def cmd_clean(ctx: CommandContext) -> None:
    """Delete a specified number of messages from the current channel."""
    try:
        max_count = int(ctx.args[0])
    except (ValueError, IndexError):
        max_count = 10

    # Clamp between 1 and 100 messages.
    if max_count > 100:
        max_count = 100
    if max_count < 1:
        await ctx.respond(content="Le nombre doit être compris entre 1 et 100.")
        return

    # Slash commands have no command message in the channel to clean up.
    limit = max_count + (0 if ctx.is_slash else 1)
    messages = [m async for m in ctx.channel.history(limit=limit)]
    cleaning_msg = await ctx.respond(content="Cleaning...", ephemeral=ctx.ephemeral)
    for message in messages:
        await message.delete()
        await sleep(0.5)
    # The first slash response returns None (interaction responses expose no
    # message object), so only delete the status message when we got one.
    if cleaning_msg is not None:
        await cleaning_msg.delete()
    await ctx.respond(
        content=f"🧹 **{len(messages)}** message(s) supprimé(s).",
        ephemeral=ctx.ephemeral,
    )


async def cmd_incscore(ctx: CommandContext) -> None:
    """Show the equity leaderboard (shared by /incscore and !incscore)."""
    records = await leaderboard()
    if not records:
        await ctx.respond(content="Aucun joueur enregistré.")
        return

    top_usr = await ctx.client.fetch_user(records[0].user_id)
    bottom_usr = await ctx.client.fetch_user(records[-1].user_id)
    pages = fmt.render_leaderboard_pages(
        records, top_usr.display_avatar.url, bottom_usr.display_avatar.url
    )
    await ctx.show_pages(pages)


async def cmd_help(ctx: CommandContext) -> None:
    """List available commands (shared by /commands and !commands)."""
    await ctx.respond(embed=fmt.render_help(ctx.prefix))


__all__ = [
    "CHAT_SYSTEM_PROMPT",
    "DISCORD_CHAR_LIMIT",
    "cmd_aup",
    "cmd_chat",
    "cmd_clean",
    "cmd_help",
    "cmd_inc",
    "cmd_incscore",
    "cmd_random",
]


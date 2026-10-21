"""Shared command handlers — one implementation per command, used by ``!`` and ``/``.

Every function follows the same shape:

    parse ctx.args  ->  call models  ->  render with views  ->  await ctx.respond(...)

Both controllers build a :class:`tetrabot.controllers.context.CommandContext`
and dispatch here, so the exact same code runs for both invocation styles.
Nothing in this package imports a controller module or touches
``message``/``interaction`` directly.
"""
from __future__ import annotations

import logging
import random
from asyncio import sleep

from tetrabot.controllers.context import CommandContext
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
    "DISCORD_CHAR_LIMIT",
    "cmd_aup",
    "cmd_clean",
    "cmd_help",
    "cmd_inc",
    "cmd_incscore",
    "cmd_random",
]


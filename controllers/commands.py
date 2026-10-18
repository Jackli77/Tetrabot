"""CONTROLLER layer: transport-agnostic command implementations.

Each ``cmd_*`` function follows the same shape:

    parse ctx.args  ->  call models  ->  render with views  ->  await ctx.respond(...)

Prefix (``!``) and slash (``/``) transports both build a
:class:`CommandContext` and dispatch through ``controllers.LOGIC``, so the
exact same code runs for both.  Nothing in here imports a transport module or
touches ``message``/``interaction`` directly.

To add a new command:
    1. Write ``async def cmd_foo(ctx)`` here (auto-registered in ``LOGIC``).
    2. Add a metadata-only prefix class in ``controllers/prefix/foo.py``.
    3. Add a thin slash wrapper in ``controllers/slash.py``.
"""
from __future__ import annotations

import random
from asyncio import sleep

import discord

from controllers.context import CommandContext
from models import duels
from models.stats import get_stats, leaderboard, record_result
from views import formatting as fmt


async def cmd_inc(ctx: CommandContext):
    """Display the caller's current stats (games, equity, winrate)."""
    aut_usr = await ctx.client.fetch_user(ctx.user_id)
    # gain=0: no equity/win/loss change (the games-played counter still ticks).
    stats = await get_stats(ctx.user_id)
    await ctx.respond(content=fmt.render_stats(aut_usr.display_name, stats))


async def cmd_random(ctx: CommandContext):
    """Roll a random number between min and max (default 1 to 100)."""
    lower, upper = 1, 100

    # Parse arguments based on count.
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

    aut_usr = await ctx.client.fetch_user(ctx.user_id)
    rolled = random.randint(lower, upper + 1)
    await ctx.respond(
        content=fmt.render_roulette(aut_usr.display_name, lower, upper, rolled)
    )


async def cmd_aup(ctx: CommandContext):
    """Ping the target and repeatedly ask them to come ("au pied")."""
    toutou = ctx.args[0] if ctx.args else ctx.author.mention
    await ctx.respond(content=fmt.render_aup_call(toutou))
    await sleep(10)
    await ctx.respond(content=fmt.render_aup_call(toutou))
    await sleep(5)
    await ctx.respond(content=fmt.render_aup_urge(toutou))
    await sleep(5)
    await ctx.respond(content=fmt.render_aup_call(toutou))


async def cmd_clean(ctx: CommandContext):
    """Delete a specified number of messages from the current channel."""
    # Parse the count argument.
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
    limit = max_count + (0 if ctx.extra.get("slash") else 1)
    messages = [m async for m in ctx.channel.history(limit=limit)]
    cleaning_msg = await ctx.respond(
        content="Cleaning...", ephemeral=getattr(ctx, "_ephemeral", False)
    )
    for message in messages:
        await message.delete()
        await sleep(0.5)
    # The first slash response returns None (interaction responses expose no
    # message object), so only delete the status message when we got one.
    if cleaning_msg is not None:
        await cleaning_msg.delete()
    await ctx.respond(
        content=f"🧹 **{len(messages)}** message(s) supprimé(s).",
        ephemeral=getattr(ctx, "_ephemeral", False),
    )



async def cmd_incscore(ctx: CommandContext):
    """Build the equity leaderboard pages (shared by /incscore and !incscore)."""
    records = await leaderboard()
    if not records:
        return None
    top_usr = await ctx.client.fetch_user(records[0].user_id)
    bottom_usr = await ctx.client.fetch_user(records[-1].user_id)
    return fmt.render_leaderboard_pages(
        records, top_usr.display_avatar.url, bottom_usr.display_avatar.url
    )


async def cmd_gamble(ctx: CommandContext, opponent: discord.User, upper: int):
    """Dice-roll duel between the caller and ``opponent`` (shared core logic)."""
    lower = 1
    challenger = ctx.author
    rolls = duels.roll_gamble(upper)
    await ctx.respond(
        content=fmt.render_gamble_intro(challenger.mention, opponent.mention, lower, upper)
    )
    await sleep(2)
    await ctx.respond(content=fmt.render_gamble_roll(challenger.display_name, rolls[0]))
    await sleep(2)
    await ctx.respond(content=fmt.render_gamble_roll(opponent.display_name, rolls[1]))
    await sleep(2)

    result = duels.resolve_gamble(ctx.user_id, opponent.id, upper, rolls)
    if result.is_tie:
        await ctx.respond(content=fmt.render_gamble_tie())
        # A tie still counts as a game played for both players: gain=0 leaves
        # equity/win/loss untouched but the games-played counter ticks
        # (same behaviour as the pre-refactor incdb helper).
        challenger_rec = await record_result(ctx.user_id, 0)
        opponent_rec = await record_result(opponent.id, 0)
    else:
        won = result.winner_id == ctx.user_id
        winner, loser = (challenger, opponent) if won else (opponent, challenger)
        await ctx.respond(
            content=fmt.render_gamble_winner(
                winner.display_name, loser.display_name, result.diff, result.decisive
            )
        )
        # Persist BOTH sides of the wager: the winner gains the difference,
        # the loser loses it (mirrors cmd_crit so equity always balances).
        challenger_rec = await record_result(ctx.user_id, result.diff if won else -result.diff)
        opponent_rec = await record_result(opponent.id, -result.diff if won else result.diff)

    await ctx.respond(content=fmt.render_score(challenger.display_name, challenger_rec))
    await ctx.respond(content=fmt.render_score(opponent.display_name, opponent_rec))


async def cmd_crit(ctx: CommandContext, opponent: discord.User, argent: int, odds: int):
    """Critical-hit duel between the caller and ``opponent`` (shared core logic)."""
    challenger = ctx.author
    crit1 = 0
    crit2 = 0
    manche = 0
    slep = 1
    while crit1 == crit2:
        manche += 1
        await ctx.respond(content=fmt.render_crit_round(manche))
        await sleep(slep)

        crited1 = duels.crit_roll(odds)
        await ctx.respond(
            content=fmt.render_crit_hit(challenger.display_name)
            if crited1
            else fmt.render_crit_miss(challenger.display_name)
        )
        if crited1:
            crit1 += 1
        await sleep(slep)

        crited2 = duels.crit_roll(odds)
        await ctx.respond(
            content=fmt.render_crit_hit(opponent.display_name)
            if crited2
            else fmt.render_crit_miss(opponent.display_name)
        )
        if crited2:
            crit2 += 1

        # The stake doubles when both players crit in the same round.
        new_stake = duels.escalate_stake(argent, crited1 and crited2)
        if new_stake != argent:
            argent = new_stake
            await ctx.respond(content=fmt.render_crit_escalation(argent))

    await sleep(slep)
    result = duels.resolve_crit(ctx.user_id, opponent.id, crit1, crit2, manche, argent)
    won = result.winner_id == ctx.user_id
    winner, loser = (challenger, opponent) if won else (opponent, challenger)
    await ctx.respond(
        content=fmt.render_crit_outcome(
            result.rounds, result.ties, winner.display_name, loser.display_name, argent
        )
    )
    challenger_rec = await record_result(ctx.user_id, argent if won else -argent)
    opponent_rec = await record_result(opponent.id, -argent if won else argent)
    await ctx.respond(content=fmt.render_score(challenger.display_name, challenger_rec))
    await ctx.respond(content=fmt.render_score(opponent.display_name, opponent_rec))


async def cmd_help(ctx: CommandContext):
    """List available commands (shared by /commands and !commands)."""
    # Imported lazily: the prefix/dm routers import command classes, whose
    # handlers dispatch back into this module (no import cycle at load time).
    from controllers.dm.router import DMS_HANDLERS
    from controllers.prefix.router import COMMAND_HANDLERS

    await ctx.respond(embed=fmt.render_help(ctx.prefix, COMMAND_HANDLERS, DMS_HANDLERS))

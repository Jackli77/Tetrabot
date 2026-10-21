"""The duel commands — ``!gamble`` and ``!crit`` (and their ``/`` twins).

Both duels follow the same three steps:

1. announce the challenge and wait for an opponent (the *transport* decides
   how: a ``✅`` reaction for ``!``, a button for ``/``),
2. play the duel round by round,
3. persist the result for **both** players.

Step 1 is the only transport-specific part, and it is hidden behind
:meth:`tetrabot.context.CommandContext.ask_for_opponent`.
"""
from __future__ import annotations

import logging
from asyncio import sleep

import discord

from tetrabot.context import ChallengeRequest, CommandContext
from tetrabot.models import duels
from tetrabot.models.stats import record_result
from tetrabot.views import formatting as fmt

logger = logging.getLogger(__name__)

#: Default crit chance (percentage) when the caller does not specify one.
DEFAULT_ODDS = 15

#: Accepted range for the crit chance.
MIN_ODDS = 10
MAX_ODDS = 90


async def _resolve_user(ctx: CommandContext, user) -> discord.User:
    """Resolve a user object into a full Discord user.

    The prefix transport hands over the user it got from the reaction event;
    the slash transport hands over ``interaction.user``.  Both may be partial
    objects, so the id is used to fetch the real user when possible.
    """
    user_id = getattr(user, "id", None)
    if ctx.client is not None and isinstance(user_id, int):
        try:
            return await ctx.client.fetch_user(user_id)
        except Exception:  # noqa: BLE001 - fall back to the object we have
            pass
    return user


async def cmd_gamble(ctx: CommandContext) -> None:
    """Dice-roll duel between the caller and whoever accepts the challenge."""
    try:
        upper = int(ctx.args[0])
    except (IndexError, ValueError):
        await ctx.respond(content="Ecris la somme maximale séparée d'un espace")
        return

    if upper < 1:
        await ctx.respond(
            content=f"{ctx.author.mention}, rentre un nombre strictement positif"
        )
        return

    challenger = ctx.author
    opponent = await ctx.ask_for_opponent(
        ChallengeRequest(
            title="🎲 Duel Gamble",
            description=(
                f"**{challenger.mention}** lance un gamble cappé à **{upper}** kakeras !"
            ),
        )
    )
    if opponent is None:
        await ctx.respond(
            content="⏱️ Gamble annulé (personne n'a accepté dans le temps imparti)."
        )
        return
    opponent = await _resolve_user(ctx, opponent)

    lower = 1
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
        # equity/win/loss untouched but the games-played counter ticks.
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
        challenger_rec = await record_result(
            ctx.user_id, result.diff if won else -result.diff
        )
        opponent_rec = await record_result(
            opponent.id, -result.diff if won else result.diff
        )

    await ctx.respond(content=fmt.render_score(challenger.display_name, challenger_rec))
    await ctx.respond(content=fmt.render_score(opponent.display_name, opponent_rec))


async def cmd_crit(ctx: CommandContext) -> None:
    """Critical-hit duel between the caller and whoever accepts the challenge."""
    try:
        stake = int(ctx.args[0])
    except (IndexError, ValueError):
        await ctx.respond(content="Précise la somme mise en jeu")
        return

    if stake < 0:
        await ctx.respond(
            content=f"{ctx.author.mention}, value error : pas de nombres négatifs"
        )
        return

    odds = DEFAULT_ODDS
    if len(ctx.args) > 1:
        try:
            odds = int(ctx.args[1])
        except ValueError:
            await ctx.respond(content="Précise la somme mise en jeu")
            return
        if not MIN_ODDS <= odds <= MAX_ODDS:
            await ctx.respond(
                content=(
                    f"{ctx.author.mention}, value error : odds compris entre "
                    f"{MIN_ODDS} et {MAX_ODDS}"
                )
            )
            return

    challenger = ctx.author
    opponent = await ctx.ask_for_opponent(
        ChallengeRequest(
            title="⚡ Duel Crit",
            description=(
                f"**{challenger.mention}** mise **{stake}** dans un duel de "
                f"chafer crit **{odds}%**"
            ),
        )
    )
    if opponent is None:
        await ctx.respond(
            content="⏱️ Duel annulé (personne n'a accepté dans le temps imparti)."
        )
        return
    opponent = await _resolve_user(ctx, opponent)

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
        new_stake = duels.escalate_stake(stake, crited1 and crited2)
        if new_stake != stake:
            stake = new_stake
            await ctx.respond(content=fmt.render_crit_escalation(stake))

    await sleep(slep)
    result = duels.resolve_crit(ctx.user_id, opponent.id, crit1, crit2, manche, stake)
    won = result.winner_id == ctx.user_id
    winner, loser = (challenger, opponent) if won else (opponent, challenger)
    await ctx.respond(
        content=fmt.render_crit_outcome(
            result.rounds, result.ties, winner.display_name, loser.display_name, stake
        )
    )
    challenger_rec = await record_result(ctx.user_id, stake if won else -stake)
    opponent_rec = await record_result(opponent.id, -stake if won else stake)
    await ctx.respond(content=fmt.render_score(challenger.display_name, challenger_rec))
    await ctx.respond(content=fmt.render_score(opponent.display_name, opponent_rec))


__all__ = ["DEFAULT_ODDS", "MAX_ODDS", "MIN_ODDS", "cmd_crit", "cmd_gamble"]


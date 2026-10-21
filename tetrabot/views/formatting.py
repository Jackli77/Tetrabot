"""Pure rendering helpers.

These functions format exactly what the command handlers hand them — they
never touch the database and never perform Discord I/O.  The interactive
widgets live in :mod:`tetrabot.views.widgets`, and the output adapters live
in :mod:`tetrabot.views.responders`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from tetrabot import catalog

if TYPE_CHECKING:
    from tetrabot.models.stats import Stats

# Shared custom emoji IDs.
DIE = "<:game_die:791035424507691013>"
CHEEMS = "<:8219_cheems:720974989490389043>"
MONEY_WINGS = "<:money_with_wings:791121758774231050>"
BANG = "<:bangbang:791122260046905355>"
TOUTOU = "<:bontoutou:790992228301668352>"


###############################################################################
# Simple commands
###############################################################################


def render_stats(name: str, stats: Stats) -> str:
    """!inc / — one-line stats summary."""
    return (
        f"**{name}** score:**{stats.val}** "
        f"équité:**{stats.equity}** WR:**{stats.win}/{stats.loss} {stats.winrate}%**"
    )


def render_score(name: str, stats: Stats) -> str:
    """Post-duel score line."""
    return f"**{name}** a un score de **{stats.val}** et une équité de **{stats.equity}**"


def render_roulette(name: str, lower: int, upper: int, rolled: int) -> str:
    """!random / — the dice-roll announcement."""
    return (
        f"{DIE} **{name}**. La roulette va de **{lower}** à **{upper}** {DIE}\n"
        f"{DIE} La mère d'Hugo vient de tirer un **{rolled}**! **{name}**{DIE}"
    )


def render_aup_call(toutou: str) -> str:
    return f"Au pièd,{toutou} {TOUTOU}"


def render_aup_urge(toutou: str) -> str:
    return f"Viens ici {toutou} et fais waf {TOUTOU}"


###############################################################################
# Chat (Ollama LLM)
###############################################################################


def render_chat(answer: str) -> str:
    """!chat / — the Ollama LLM answer, rendered as a quote block."""
    return f"> 🤖 {answer}"


###############################################################################
# Gamble duel
###############################################################################


def render_gamble_intro(challenger_mention: str, opponent_mention: str, lower: int, upper: int) -> str:
    return (
        f"{DIE} {challenger_mention} vs {opponent_mention}. "
        f"La roulette va de **{lower}** à **{upper}** {DIE}"
    )


def render_gamble_roll(name: str, rolled: int) -> str:
    return f"{DIE} {name} a tiré **{rolled}**! {DIE}"


def render_gamble_tie() -> str:
    return f"{CHEEMS} égalité pas de gagnant {CHEEMS}"


def render_gamble_winner(winner_name: str, loser_name: str, diff: int, decisive: bool) -> str:
    verb = "s'est bien fait baiser et doit" if decisive else "doit"
    return (
        f"{DIE} Le gagnant est **{winner_name}**! "
        f"**{loser_name}** {verb} **{diff}** kakeras à **{winner_name}** {DIE}"
    )


###############################################################################
# Crit duel
###############################################################################


def render_crit_round(manche: int) -> str:
    return f"__**Manche {manche}**__"


def render_crit_hit(name: str) -> str:
    return f"**{name}** Coup critique!{BANG}"


def render_crit_miss(name: str) -> str:
    return f"Pas de chance, **{name}** {CHEEMS}"


def render_crit_escalation(stake: int) -> str:
    return f"La somme en jeu passe à **{stake}** {MONEY_WINGS}"


def render_crit_outcome(rounds: int, ties: int, winner_name: str, loser_name: str, stake: int) -> str:
    return (
        f"Le duel s'est terminé après **{rounds}** manches et **{ties}** égalités\n"
        f"Le gagnant est **{winner_name}**, **{loser_name}** doit donner **{stake}** "
        f"à **{winner_name}** {MONEY_WINGS}"
    )


###############################################################################
# Shared controller replies (used by both transports)
###############################################################################


def render_missing_arguments(mention: str, required: int) -> str:
    """The reply sent when a command is called without enough arguments.

    ``required`` is the number of arguments the command expects, so the
    message states how many are needed in total.
    """
    return f"{mention} Cette fonction à besoin de minimum {required} arguments"


def render_challenge_embed(title: str, description: str) -> discord.Embed:
    """The embed announcing a duel challenge.

    Shared by both transports: the ``!`` transport adds a ``✅`` reaction to
    it, the ``/`` transport attaches an accept button.
    """
    return discord.Embed(
        title=title,
        description=description,
        colour=discord.Colour.gold(),
    )


###############################################################################
# Help embed (used by /commands, !commands, and the DM help command)
###############################################################################


def command_line(prefix: str, spec: catalog.CommandSpec) -> str:
    """Format one help line from a catalog entry.

    Aliases are listed as annotations instead of being rendered as separate
    commands.
    """
    usage = spec.usage()
    usage = f" {usage}" if usage else ""
    alias_str = ""
    if spec.aliases:
        aliases = ", ".join(f"`{prefix}{a}`" for a in spec.aliases)
        alias_str = f" *(alias: {aliases})*"
    return f"`{prefix}{spec.name}{usage}`{alias_str} — {spec.description.rstrip('.')}"


def command_lines(prefix: str, specs: tuple[catalog.CommandSpec, ...]) -> list[str]:
    """Help lines for a group of catalog entries."""
    return [command_line(prefix, spec) for spec in specs]


def render_help(prefix: str) -> discord.Embed:
    """The shared help embed with one field per command group."""
    embed = discord.Embed(
        title="📝 Commandes disponibles",
        description=f"Préfixe de commande : `{prefix}`",
        colour=discord.Colour.blue(),
    )
    server_lines = command_lines(prefix, catalog.guild_commands())
    if server_lines:
        embed.add_field(
            name="💬 Commandes de serveur",
            value="\n".join(server_lines),
            inline=False,
        )
    dm_lines = command_lines(prefix, catalog.dm_commands())
    if dm_lines:
        embed.add_field(
            name="📩 Commandes en message privé (DM)",
            value="\n".join(dm_lines),
            inline=False,
        )
    return embed


###############################################################################
# Leaderboard pages (shared by !incscore and /incscore)
###############################################################################


def _member_line(record: Stats) -> str:
    return (
        f"**{record.display_name}** — **WR:** {record.win}/{record.loss} ({record.winrate}%)"
        f" — **Équité:** {record.equity}"
    )


def render_leaderboard_pages(
    records: list[Stats],
    top_avatar_url: str,
    bottom_avatar_url: str,
) -> list[discord.Embed]:
    """Three embed pages: member list, biggest winner, biggest loser."""
    top, bottom = records[0], records[-1]

    page1 = discord.Embed(title="🏆 Classement d'équité", colour=discord.Colour.lighter_grey())
    page1.set_thumbnail(url=top_avatar_url)
    page1.add_field(
        name="Membres",
        value="\n ".join(_member_line(r) for r in records),
        inline=False,
    )

    page2 = discord.Embed(
        title="🥇 Grand gagnant",
        description=(
            f"**{top.display_name}** avec une équité de **{top.equity}** "
            f"et un winrate de **{top.win}/{top.loss} ({top.winrate}%)**"
        ),
        colour=discord.Colour.green(),
    )
    page2.set_thumbnail(url=top_avatar_url)

    page3 = discord.Embed(
        title="💀 Grand perdant",
        description=(
            f"**{bottom.display_name}** avec une équité de **{bottom.equity}** "
            f"et un winrate de **{bottom.win}/{bottom.loss} ({bottom.winrate}%)**"
        ),
        colour=discord.Colour.red(),
    )
    page3.set_thumbnail(url=bottom_avatar_url)

    return [page1, page2, page3]


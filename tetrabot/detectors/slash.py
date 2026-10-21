"""DETECTOR/``/``: recognise native slash invocations on the command tree.

:class:`SlashDetector` registers every Discord slash (app) command on the
bot's command tree.  The commands themselves are **generated from the
catalog** (:mod:`tetrabot.catalog`), so the ``/`` tree and the ``!`` router
can never drift apart.

Each generated command builds a shared :class:`tetrabot.context.CommandContext`
and dispatches to the same shared logic the ``!`` detector uses.  Interactive
UI widgets (challenge buttons, leaderboard pagination) live in
:mod:`tetrabot.views.widgets`.
"""
from __future__ import annotations

import inspect
import logging
from typing import Any

import discord
from discord import app_commands

from tetrabot import catalog
from tetrabot.context import ChallengeRequest, CommandContext, SlashResponder
from tetrabot.detectors.base import BaseDetector, DetectionResult
from tetrabot.views.widgets import ChallengeView, LeaderboardPaginationView

logger = logging.getLogger(__name__)

#: How long a duel challenge stays open, in seconds.
CHALLENGE_TIMEOUT = 45.0


def _option_annotation(param: catalog.Param) -> Any:
    """The Discord type annotation for a catalog parameter.

    Integer parameters become a ``Range`` so Discord itself enforces the
    bounds declared in the catalog.
    """
    if param.type is int and (param.minimum is not None or param.maximum is not None):
        return app_commands.Range[
            int,
            param.minimum if param.minimum is not None else 0,
            param.maximum if param.maximum is not None else None,
        ]
    if param.type is int:
        return int
    return str


def _build_callback(spec: catalog.CommandSpec):
    """Build the Discord callback for a catalog entry.

    The signature is generated from the catalog so Discord knows the option
    names, types and bounds — and so the callback always matches them.
    """
    params = spec.slash_params or spec.params

    async def callback(interaction: discord.Interaction, **kwargs):
        from tetrabot.commands import LOGIC

        ctx = build_context(interaction, spec)
        # Only the options the user actually filled in are forwarded.
        ctx.args = [str(value) for value in kwargs.values() if value is not None]
        ctx.extra.update({k: v for k, v in kwargs.items() if v is not None})

        if spec.name in CHALLENGE_COMMANDS:
            ctx.challenge = _make_challenge_handler(interaction)
        ctx.paginate = _make_pagination_handler(interaction, ctx.respond)

        await LOGIC[spec.logic](ctx)

    # Give the callback the signature Discord expects.
    parameters = [
        inspect.Parameter(
            "interaction", inspect.Parameter.POSITIONAL_OR_KEYWORD
        )
    ]
    for param in params:
        default = inspect.Parameter.empty if param.required else param.default
        parameters.append(
            inspect.Parameter(
                param.name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=_option_annotation(param),
                default=default,
            )
        )
    callback.__signature__ = inspect.Signature(parameters)

    # Discord reads the option descriptions from this mapping.
    descriptions = {p.name: p.description for p in params if p.description}
    if descriptions:
        callback.__discord_app_commands_param_description__ = descriptions
    return callback


def build_context(
    interaction: discord.Interaction,
    spec: catalog.CommandSpec | None = None,
) -> CommandContext:
    """Build the shared :class:`CommandContext` for a slash command."""
    return CommandContext(
        author=interaction.user,
        channel=interaction.channel,
        client=interaction.client,
        args=[],
        respond=SlashResponder(interaction),
        prefix="/",
        ephemeral=spec.ephemeral if spec is not None else False,
    )


class SlashDetector(BaseDetector):
    """Register the ``/`` command tree.

    Detection for slash commands happens inside Discord itself (the user
    picks a registered command); this class only wires the tree so every
    invocation normalises into a :class:`CommandContext` and reaches the
    shared logic.
    """

    name = "/"

    def __init__(self, bot: discord.Client | None = None):
        self.bot = bot

    async def detect(self, interaction: discord.Interaction, bot_client=None):
        """Slash invocations always dispatch via the tree — nothing to parse."""
        return DetectionResult(handled=True, extra={"slash": True})

    def setup(self, bot: discord.Client, tree: app_commands.CommandTree):
        """Register every slash command on ``tree``."""
        self.bot = bot
        setup_slash_commands(bot, tree)
        return tree


def _make_challenge_handler(interaction: discord.Interaction) -> Any:
    """Build the button-based challenge used by the duel commands.

    The slash transport offers a button; the prefix transport offers a
    reaction.  Both end up calling the same shared logic.
    """

    async def challenge(request: ChallengeRequest) -> discord.User | None:
        view = ChallengeView(challenger=interaction.user, timeout=CHALLENGE_TIMEOUT)
        embed = discord.Embed(
            title=request.title,
            description=request.description,
            colour=discord.Colour.gold(),
        )
        await interaction.response.send_message(embed=embed, view=view)

        await view.wait()
        if view.accepted_by is None:
            return None
        await interaction.followup.send(
            f"**{view.accepted_by.mention}** a accepté le challenge de "
            f"{interaction.user.mention}"
        )
        return view.accepted_by

    return challenge


def _make_pagination_handler(
    interaction: discord.Interaction,
    responder: SlashResponder,
) -> Any:
    """Build the button-based pagination used by the ``/`` commands.

    The page is sent through the shared ``responder`` so the interaction is
    only ever responded to once, even if the command sends something else
    afterwards.
    """

    async def paginate(pages: list[discord.Embed]) -> None:
        view = LeaderboardPaginationView(pages=pages, author_id=interaction.user.id)
        await responder(embed=pages[0], view=view)

    return paginate


#: Commands that need a duel challenge instead of a plain dispatch.
CHALLENGE_COMMANDS = {"gamble", "crit"}


def setup_slash_commands(bot: discord.Client, tree: app_commands.CommandTree) -> None:
    """Register every slash command described by the catalog.

    Each command is generated from its :class:`tetrabot.catalog.CommandSpec`:
    the options come from the catalog, and the callback dispatches to the
    same shared logic the ``!`` detector uses.
    """
    for spec in catalog.slash_commands():
        for name in spec.slash_name_list:
            _register_slash_command(bot, tree, spec, name)


def _register_slash_command(
    bot: discord.Client,
    tree: app_commands.CommandTree,
    spec: catalog.CommandSpec,
    name: str,
) -> None:
    """Register one slash command built from its catalog entry."""
    callback = _build_callback(spec)
    command = app_commands.Command(
        name=name,
        description=spec.description,
        callback=callback,
    )
    tree.add_command(command)


__all__ = [
    "CHALLENGE_COMMANDS",
    "CHALLENGE_TIMEOUT",
    "SlashDetector",
    "build_context",
    "setup_slash_commands",
]

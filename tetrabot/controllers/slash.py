"""CONTROLLER/``/``: the slash transport.

:class:`SlashController` registers every Discord slash (app) command on the
bot's command tree.  The commands themselves are **generated from the
catalog** (:mod:`tetrabot.catalog`), so the ``/`` tree and the ``!`` router
can never drift apart.

Each generated command builds a shared :class:`tetrabot.controllers.context.CommandContext`
and dispatches to the same shared handler the ``!`` controller uses.
Interactive UI widgets (challenge buttons, leaderboard pagination) live in
:mod:`tetrabot.views.widgets`.
"""
from __future__ import annotations

import inspect
import logging
from typing import Any

import discord
from discord import app_commands

from tetrabot import catalog
from tetrabot.controllers.base import BaseController, DetectionResult
from tetrabot.controllers.context import ChallengeRequest, CommandContext
from tetrabot.views.formatting import render_challenge_embed
from tetrabot.views.responders import SlashResponder
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


class SlashController(BaseController):
    """Register the ``/`` command tree.

    Detection for slash commands happens inside Discord itself (the user
    picks a registered command); this class only wires the tree so every
    invocation normalises into a :class:`CommandContext` and reaches the
    shared handler.
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

    # -- transport specific steps --------------------------------------

    def build_context(
        self, spec: catalog.CommandSpec, result: DetectionResult, interaction, bot_client
    ) -> CommandContext:
        """Build the shared context for a slash invocation."""
        ctx = build_context(interaction, spec)
        if spec.needs_challenge:
            ctx.challenge = _make_challenge_handler(interaction)
        ctx.paginate = _make_pagination_handler(interaction, ctx.respond)
        ctx.typing = _make_typing_handler(interaction)
        return ctx


def _make_typing_handler(interaction: discord.Interaction) -> Any:
    """Build the "bot is typing" indicator for the ``/`` transport."""

    def typing():
        return interaction.channel.typing()

    return typing


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

def _build_callback(spec: catalog.CommandSpec):
    """Build the Discord callback for a catalog entry.

    The signature is generated from the catalog so Discord knows the option
    names, types and bounds — and so the callback always matches them.
    """
    params = spec.slash_params or spec.params

    async def callback(interaction: discord.Interaction, **kwargs):
        controller = SlashController()
        result = await controller.detect(interaction)
        ctx = controller.build_context(spec, result, interaction, interaction.client)
        # Only the options the user actually filled in are forwarded.
        ctx.args = [str(value) for value in kwargs.values() if value is not None]
        ctx.extra.update({k: v for k, v in kwargs.items() if v is not None})

        await controller.execute(spec, ctx)

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


def _make_challenge_handler(interaction: discord.Interaction) -> Any:
    """Build the button-based challenge used by the duel handlers.

    The slash transport offers a button; the prefix transport offers a
    reaction.  Both end up calling the same shared handler.
    """

    async def challenge(request: ChallengeRequest) -> discord.User | None:
        view = ChallengeView(challenger=interaction.user, timeout=CHALLENGE_TIMEOUT)
        await interaction.response.send_message(
            embed=render_challenge_embed(request.title, request.description), view=view
        )

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


def setup_slash_commands(bot: discord.Client, tree: app_commands.CommandTree) -> None:
    """Register every slash command described by the catalog.

    Each command is generated from its :class:`tetrabot.catalog.CommandSpec`:
    the options come from the catalog, and the callback dispatches to the
    same shared handler the ``!`` controller uses.
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
    "CHALLENGE_TIMEOUT",
    "SlashController",
    "build_context",
    "setup_slash_commands",
]

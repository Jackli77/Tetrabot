"""CONTROLLER/``!``: the prefix transport.

:class:`PrefixController` runs the three detection steps in order and stops at
the first miss (all misses are silent, to avoid spamming channels shared
with other bots):

1. ``_ignore_self`` — drop the bot's own messages (anti-loop guard).
2. ``_route`` — flag DMs so the right set of commands is used.
3. ``_parse_prefix`` — parse ``!command args`` (lowercased command name).

:func:`handle_message` runs detection and dispatches to the shared pipeline
in :class:`tetrabot.controllers.base.BaseController`, which builds a
:class:`tetrabot.controllers.context.CommandContext` and calls the same
shared handler the ``/`` controller uses.

The list of available commands comes from :mod:`tetrabot.catalog`, so adding
a command never means touching this file.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import discord

from tetrabot import catalog, config
from tetrabot.controllers.base import BaseController, DetectionResult
from tetrabot.controllers.context import ChallengeRequest, CommandContext
from tetrabot.views.formatting import render_challenge_embed, render_missing_arguments
from tetrabot.views.responders import PrefixResponder

logger = logging.getLogger(__name__)

#: How long a duel challenge stays open, in seconds.
CHALLENGE_TIMEOUT = 45.0


class PrefixController(BaseController):
    """Detect ``!command args`` invocations in Discord messages."""

    name = "!"

    def __init__(self, prefix: str | None = None):
        self.prefix = prefix if prefix is not None else config.COMMAND_PREFIX

    def _ignore_self(self, message, bot_client, result: DetectionResult) -> bool:
        """Return False (stop) when the message was sent by the bot itself."""
        if message.author == bot_client.user:
            result.handled = False
            return False
        return True

    def _route(self, message, bot_client, result: DetectionResult) -> bool:
        """Flag DMs so the right set of commands is used."""
        result.is_dm = message.channel == getattr(message.author, "dm_channel", None)
        return True

    def _parse_prefix(self, message, bot_client, result: DetectionResult) -> bool:
        """Parse the command prefix; stop silently when the message has none."""
        text = message.content or ""
        if not text.startswith(self.prefix) or text == self.prefix:
            result.handled = False
            return False
        parts = text[len(self.prefix):].split()
        result.command = parts[0].lower()
        result.args = parts[1:]
        return True

    async def detect(self, message, bot_client) -> DetectionResult:
        """Run every step in order; stop at the first miss."""
        result = DetectionResult()
        for step in (self._ignore_self, self._route, self._parse_prefix):
            if not step(message, bot_client, result):
                break
        return result

    # -- transport specific steps --------------------------------------

    def build_context(
        self, spec: catalog.CommandSpec, result: DetectionResult, message, bot_client
    ) -> CommandContext:
        """Build the shared context for a prefix invocation."""
        ctx = CommandContext(
            author=message.author,
            channel=message.channel,
            client=bot_client,
            args=list(result.args),
            respond=PrefixResponder(message),
            prefix=config.COMMAND_PREFIX,
            ephemeral=spec.ephemeral,
        )
        ctx.challenge = _make_challenge_handler(message, bot_client)
        ctx.paginate = _make_pagination_handler(message, bot_client)
        ctx.typing = _make_typing_handler(message)
        return ctx

    # -- shared steps ---------------------------------------------------

    def is_available(self, spec: catalog.CommandSpec, result: DetectionResult) -> bool:
        """Honour the scope declared in the catalog (guild / DM / both)."""
        if result.is_dm:
            return spec.scope.allows_dm
        return spec.scope.allows_guild

    async def validate(
        self, spec: catalog.CommandSpec, result: DetectionResult, message, bot_client
    ) -> bool:
        """Check that every required parameter was supplied."""
        if len(result.args) >= len(spec.required_params):
            return True
        await message.channel.send(
            content=render_missing_arguments(
                message.author.mention, len(spec.required_params)
            )
        )
        return False


def _make_challenge_handler(
    message,
    bot_client,
) -> Callable[[ChallengeRequest], Awaitable[discord.User | None]]:
    """Build the ``✅``-reaction challenge used by the duel handlers.

    The challenger cannot accept their own challenge, and bots never count.
    """

    async def challenge(request: ChallengeRequest) -> discord.User | None:
        bet_msg = await message.channel.send(
            embed=render_challenge_embed(request.title, request.description)
        )
        await bet_msg.add_reaction(request.emoji)

        def check(reaction, user):
            return (
                str(reaction.emoji) == request.emoji
                and reaction.message == bet_msg
                and not user.bot
                and user.id != message.author.id
            )

        try:
            _reaction, user = await bot_client.wait_for(
                "reaction_add", timeout=CHALLENGE_TIMEOUT, check=check
            )
        except asyncio.TimeoutError:
            return None
        return user

    return challenge


def _make_typing_handler(message) -> Callable[[], Any]:
    """Build the "bot is typing" indicator for the ``!`` transport."""

    def typing():
        return message.channel.typing()

    return typing


def _make_pagination_handler(
    message,
    bot_client,
) -> Callable[[list[discord.Embed]], Awaitable[None]]:
    """Build the reaction-based pagination used by the ``!`` commands."""

    async def paginate(pages: list[discord.Embed]) -> None:
        from tetrabot.views.widgets import paginate_with_reactions

        await paginate_with_reactions(message, bot_client, pages)

    return paginate


async def handle_message(message, bot_client, controller: PrefixController | None = None):
    """Detect a ``!`` invocation in ``message`` and dispatch to its handler.

    Does nothing (silently) when the message is not a ``!`` command.
    """
    controller = controller or PrefixController()
    result = await controller.detect(message, bot_client)

    if not result.handled or result.command is None:
        return result

    spec = catalog.find(result.command)
    if spec is None:
        # Unknown command: stay silent, to avoid spamming channels shared
        # with other bots that use the same prefix.
        return result

    logger.info(
        "%s: %s%s %s",
        message.author.name,
        config.COMMAND_PREFIX,
        result.command,
        " ".join(result.args),
    )

    await controller.dispatch(spec, result, message, bot_client)
    return result


__all__ = ["CHALLENGE_TIMEOUT", "DetectionResult", "PrefixController", "handle_message"]

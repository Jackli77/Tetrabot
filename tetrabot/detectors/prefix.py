"""DETECTOR/``!``: recognise prefix invocations in Discord messages.

:class:`PrefixDetector` runs the three detection steps in order and stops at
the first miss (all misses are silent, to avoid spamming channels shared
with other bots):

1. ``_ignore_self`` — drop the bot's own messages (anti-loop guard).
2. ``_route`` — flag DMs so the right set of commands is used.
3. ``_parse_prefix`` — parse ``!command args`` (lowercased command name).

:func:`handle_message` runs detection and dispatches to the chosen handler,
which builds a shared :class:`tetrabot.context.CommandContext` and calls the
same shared logic the ``/`` detector uses.

The list of available commands comes from :mod:`tetrabot.catalog`, so adding
a command never means touching this file.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import discord

from tetrabot import catalog, config
from tetrabot.context import ChallengeRequest, CommandContext, PrefixResponder
from tetrabot.detectors.base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)

#: How long a duel challenge stays open, in seconds.
CHALLENGE_TIMEOUT = 45.0


class PrefixDetector(BaseDetector):
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


def _build_context(
    spec: catalog.CommandSpec,
    args: list[str],
    message,
    bot_client,
) -> CommandContext:
    """Build the shared context for a prefix invocation."""
    return CommandContext(
        author=message.author,
        channel=message.channel,
        client=bot_client,
        args=list(args),
        respond=PrefixResponder(message),
        prefix=config.COMMAND_PREFIX,
        ephemeral=spec.ephemeral,
    )


def _make_challenge_handler(
    message,
    bot_client,
) -> Callable[[ChallengeRequest], Awaitable[discord.User | None]]:
    """Build the ``✅``-reaction challenge used by the duel commands.

    The challenger cannot accept their own challenge, and bots never count.
    """

    async def challenge(request: ChallengeRequest) -> discord.User | None:
        embed = discord.Embed(
            title=request.title,
            description=request.description,
            colour=discord.Colour.gold(),
        )
        bet_msg = await message.channel.send(embed=embed)
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


def _make_pagination_handler(
    message,
    bot_client,
) -> Callable[[list[discord.Embed]], Awaitable[None]]:
    """Build the reaction-based pagination used by the ``!`` commands."""

    async def paginate(pages: list[discord.Embed]) -> None:
        from tetrabot.views.widgets import paginate_with_reactions

        await paginate_with_reactions(message, bot_client, pages)

    return paginate


async def handle_message(message, bot_client, detector: PrefixDetector | None = None):
    """Detect a ``!`` invocation in ``message`` and dispatch to its handler.

    Does nothing (silently) when the message is not a ``!`` command.
    """
    detector = detector or PrefixDetector()
    result = await detector.detect(message, bot_client)

    if not result.handled or result.command is None:
        return result

    spec = catalog.find(result.command)
    if spec is None:
        # Unknown command: stay silent, to avoid spamming channels shared
        # with other bots that use the same prefix.
        return result

    if result.is_dm and not spec.scope.allows_dm:
        return result
    if not result.is_dm and not spec.scope.allows_guild:
        return result

    logger.info(
        "%s: %s%s %s",
        message.author.name,
        config.COMMAND_PREFIX,
        result.command,
        " ".join(result.args),
    )

    # Check that every required parameter was supplied.
    if len(result.args) < len(spec.required_params):
        await message.channel.send(
            content=(
                f"{message.author.mention} Cette fonction à besoin de minimum {len(spec.required_params)} arguments"
            )
        )
        return result

    ctx = _build_context(spec, result.args, message, bot_client)
    ctx.challenge = _make_challenge_handler(message, bot_client)
    ctx.paginate = _make_pagination_handler(message, bot_client)

    from tetrabot.commands import LOGIC

    await LOGIC[spec.logic](ctx)
    return result


__all__ = ["CHALLENGE_TIMEOUT", "DetectionResult", "PrefixDetector", "handle_message"]

"""The normalised request shared by every controller.

A :class:`CommandContext` is the transport-agnostic form of a Discord
invocation: the author, the channel, the arguments and the hooks the
transport offers (challenge, pagination).  The handlers in
:mod:`tetrabot.controllers.commands` only ever see this object, which is
what lets a single implementation serve both ``!`` and ``/``.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import discord

from tetrabot.views.responders import Responder


@dataclass(frozen=True)
class ChallengeRequest:
    """How a duel challenge should be announced.

    The *handler* decides that a duel is needed and describes it; the
    controller decides how the challenge is presented (a ``✅`` reaction for
    ``!``, a button for ``/``).
    """

    title: str
    description: str
    label: str = "Accepter le défi"
    emoji: str = "✅"


@dataclass
class CommandContext:
    """Normalised context shared by prefix and slash command handlers.

    ``args`` holds the positional arguments of the invocation (the ``!``
    arguments, or the slash options the user actually filled in).
    ``extra`` holds named values, keyed by parameter name.
    ``challenge`` is an optional hook used by the duel commands: the handler
    asks for an opponent through it, and the controller decides how the
    challenge is presented (a ``✅`` reaction for ``!``, a button for ``/``).
    """

    author: discord.abc.User
    channel: discord.abc.Messageable
    client: discord.Client
    args: list[str]
    respond: Responder
    prefix: str = "!"
    ephemeral: bool = False
    extra: dict = field(default_factory=dict)
    challenge: Callable[[ChallengeRequest], Awaitable[discord.User | None]] | None = None
    paginate: Callable[[list[discord.Embed]], Awaitable[None]] | None = None
    typing: Callable[[], Any] | None = None

    @property
    def user_id(self) -> int:
        """The author's Discord user id."""
        user_id = getattr(self.author, "id", None)
        if isinstance(user_id, int):
            return user_id
        # Fall back to parsing the mention for objects that only expose it.
        return int("".join(filter(str.isdigit, self.author.mention)))

    @property
    def is_slash(self) -> bool:
        """True when the command was invoked as a ``/`` slash command."""
        return self.prefix == "/"

    async def display_name(self) -> str:
        """The author's display name, resolved from Discord when possible."""
        if self.client is not None:
            try:
                user = await self.client.fetch_user(self.user_id)
            except Exception:
                pass
            else:
                return user.display_name
        return getattr(self.author, "display_name", None) or str(self.user_id)

    async def ask_for_opponent(self, request: ChallengeRequest) -> discord.User | None:
        """Announce a duel and wait for somebody to accept it.

        Returns the accepting user, or ``None`` when nobody accepted in time.
        Transports that cannot host a challenge never accept.
        """
        if self.challenge is None:
            return None
        return await self.challenge(request)

    async def show_pages(self, pages: list[discord.Embed]) -> None:
        """Display a list of embeds with the transport's own pagination.

        The ``!`` transport pages with reactions, the ``/`` transport with
        buttons.
        """
        if self.paginate is None:
            for page in pages:
                await self.respond(embed=page)
            return
        await self.paginate(pages)

    @asynccontextmanager
    async def typing_indicator(self):
        """Show the "bot is typing" indicator while the command runs.

        A long silence is what makes a bot feel dead; the indicator tells
        the user that something is happening.  Transports that cannot show
        it simply do nothing.
        """
        if self.typing is None:
            yield None
            return
        try:
            async with self.typing() as indicator:
                yield indicator
        except Exception:
            # A missing permission must never break the command.
            yield None


__all__ = ["ChallengeRequest", "CommandContext"]

"""The transport-agnostic command context.

Both detectors — :mod:`tetrabot.detectors.prefix` for ``!`` and
:mod:`tetrabot.detectors.slash` for ``/`` — build a :class:`CommandContext`
and hand it to the matching ``cmd_*`` function, so a single implementation
serves both invocation styles.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import discord


@dataclass(frozen=True)
class ChallengeRequest:
    """How a duel challenge should be announced.

    The *logic* decides that a duel is needed and describes it; the detector
    decides how the challenge is presented (a ``✅`` reaction for ``!``, a
    button for ``/``).
    """

    title: str
    description: str
    label: str = "Accepter le défi"
    emoji: str = "✅"


class Responder:
    """Sends a reply through the transport the command was invoked with.

    Subclasses adapt a Discord *message* (prefix) or *interaction* (slash) to
    the same tiny interface, so command logic never touches either directly.
    """

    async def __call__(
        self,
        content: str | None = None,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
        ephemeral: bool = False,
    ) -> discord.Message | None:
        raise NotImplementedError

    async def defer(self) -> None:
        """Acknowledge the invocation early (no-op where unsupported)."""


class PrefixResponder(Responder):
    """Replies to a ``!`` command by posting in the channel it came from."""

    def __init__(self, message: discord.Message):
        self.message = message

    async def __call__(
        self,
        content: str | None = None,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
        ephemeral: bool = False,
    ) -> discord.Message:
        # ``ephemeral`` is meaningless for a plain message: the flag only
        # exists so command logic can stay transport-agnostic.
        return await self.message.channel.send(content=content, embed=embed, view=view)


class SlashResponder(Responder):
    """Replies to a ``/`` command through the interaction.

    The first call uses ``interaction.response.send_message`` (or ``defer`` if
    :meth:`defer` was called first); every subsequent call uses
    ``interaction.followup.send``.  This transparently handles Discord's
    "respond once per interaction" rule.
    """

    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self._used = False

    async def __call__(
        self,
        content: str | None = None,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
        ephemeral: bool = False,
    ) -> discord.Message | None:
        kwargs = {"content": content, "embed": embed}
        if view is not None:
            kwargs["view"] = view
        if ephemeral:
            kwargs["ephemeral"] = True

        if not self._used:
            self._used = True
            # Interaction responses expose no message object.
            await self.interaction.response.send_message(**kwargs)
            return None
        await self.interaction.followup.send(**kwargs)
        return None

    async def defer(self) -> None:
        """Acknowledge the interaction now, so long commands may take their time."""
        if not self._used:
            self._used = True
            await self.interaction.response.defer()


@dataclass
class CommandContext:
    """Normalised context shared by prefix and slash command logic.

    ``args`` holds the positional arguments of the invocation (the ``!``
    arguments, or the slash options the user actually filled in).
    ``extra`` holds named values, keyed by parameter name.
    ``challenge`` is an optional hook used by the duel commands: the logic
    asks for an opponent through it, and the detector decides how the
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


__all__ = [
    "ChallengeRequest",
    "CommandContext",
    "PrefixResponder",
    "Responder",
    "SlashResponder",
]

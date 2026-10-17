"""CONTROLLER plumbing: the transport-agnostic command context.

Prefix commands (``!``) and slash commands (``/``) both build a
:class:`CommandContext` and hand it to the matching ``cmd_*`` function, so
one implementation serves both transports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional

import discord


@dataclass
class CommandContext:
    """Normalised context shared by prefix and slash command logic."""

    author: discord.abc.User
    channel: discord.abc.Messageable
    client: discord.Client
    args: List[str]
    respond: Callable[..., Awaitable]
    extra: dict = field(default_factory=dict)
    prefix: str = "!"
    _ephemeral: bool = False

    @property
    def user_id(self) -> int:
        """The author's Discord user id (mention parsing works for both transports)."""
        return int("".join(filter(str.isdigit, self.author.mention)))


def make_prefix_respond(message: discord.Message) -> Callable[..., Awaitable]:
    """Build a ``respond`` callable for prefix commands (``!``)."""

    async def respond(
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        view: Optional[discord.ui.View] = None,
        ephemeral: bool = False,
    ) -> discord.Message:
        return await message.channel.send(content=content, embed=embed, view=view)

    return respond


def make_slash_respond(interaction: discord.Interaction):
    """Build a ``respond`` callable for slash commands (``/``).

    The first call uses ``interaction.response.send_message`` (or ``defer`` if
    :meth:`respond.defer` was called first); every subsequent call uses
    ``interaction.followup.send``.  This transparently handles Discord's
    "respond once per interaction" rule.
    """
    state = {"used": False}

    async def respond(
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        view: Optional[discord.ui.View] = None,
        ephemeral: bool = False,
    ):
        kwargs = {"content": content, "embed": embed}
        if view is not None:
            kwargs["view"] = view
        if ephemeral:
            kwargs["ephemeral"] = True
        if not state["used"]:
            state["used"] = True
            await interaction.response.send_message(**kwargs)
        else:
            await interaction.followup.send(**kwargs)

    async def defer():
        if not state["used"]:
            state["used"] = True
            await interaction.response.defer()

    respond.defer = defer
    return respond

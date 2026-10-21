"""The output adapters of the VIEW layer.

A *responder* sends a rendered message back to the user through the
transport the command was invoked with.  Subclasses adapt a Discord
*message* (prefix) or *interaction* (slash) to the same tiny interface, so
the command handlers never touch either directly.
"""
from __future__ import annotations

import discord


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


__all__ = ["PrefixResponder", "Responder", "SlashResponder"]

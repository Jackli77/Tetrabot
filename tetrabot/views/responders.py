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

    async def edit(
        self,
        content: str | None = None,
        embed: discord.Embed | None = None,
    ) -> None:
        """Replace what was already sent.

        Used by the streaming chat, which rewrites its message as the answer
        grows.  Transports that cannot edit simply do nothing.
        """


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

    async def edit(
        self,
        content: str | None = None,
        embed: discord.Embed | None = None,
    ) -> None:
        """Edit the message this responder posted."""
        await self.message.edit(content=content, embed=embed)


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

    async def edit(
        self,
        content: str | None = None,
        embed: discord.Embed | None = None,
    ) -> None:
        """Edit the original response.

        Before the first answer this edits the pending response; afterwards
        it edits the message Discord already published.
        """
        kwargs = {"content": content, "embed": embed}
        if not self._used:
            self._used = True
            await self.interaction.response.edit_message(**kwargs)
            return
        await self.interaction.edit_original_response(**kwargs)


__all__ = ["PrefixResponder", "Responder", "SlashResponder"]

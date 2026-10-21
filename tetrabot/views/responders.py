"""The output adapters of the VIEW layer.

A *responder* sends a rendered message back to the user through the
transport the command was invoked with.  Subclasses adapt a Discord
*message* (prefix) or *interaction* (slash) to the same tiny interface, so
the command handlers never touch either directly.
"""
from __future__ import annotations

import logging

import discord

logger = logging.getLogger(__name__)


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
    """Replies to a ``!`` command by posting in the channel it came from.

    The responder remembers the message it posted, so :meth:`edit` rewrites
    *that* message — the bot's own placeholder — instead of the message the
    user sent.  Editing somebody else's message is forbidden on Discord.
    """

    def __init__(self, message: discord.Message):
        self.message = message
        self.sent: discord.Message | None = None

    async def __call__(
        self,
        content: str | None = None,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
        ephemeral: bool = False,
    ) -> discord.Message:
        # ``ephemeral`` is meaningless for a plain message: the flag only
        # exists so command logic can stay transport-agnostic.
        self.sent = await self.message.channel.send(
            content=content, embed=embed, view=view
        )
        return self.sent

    async def edit(
        self,
        content: str | None = None,
        embed: discord.Embed | None = None,
    ) -> None:
        """Edit the message this responder posted."""
        target = self.sent
        if target is None:
            # Nothing was posted yet: there is nothing to rewrite.
            return
        await target.edit(content=content, embed=embed)


class SlashResponder(Responder):
    """Replies to a ``/`` command through the interaction.

    The first call uses ``interaction.response.send_message`` (or ``defer`` if
    :meth:`defer` was called first); every subsequent call uses
    ``interaction.followup.send``.  This transparently handles Discord's
    "respond once per interaction" rule.

    The responder also *trusts the interaction itself*: if the interaction
    has already been answered — by a view, or by anything else — it falls
    back to a follow-up instead of raising ``InteractionResponded``.  A
    command that dies on its second message leaves the user staring at a
    half-finished answer, so this is deliberately forgiving.
    """

    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self._used = False

    def _already_answered(self) -> bool:
        """Whether the interaction has been answered already."""
        if self._used:
            return True
        response = getattr(self.interaction, "response", None)
        is_done = getattr(response, "is_done", None)
        if callable(is_done):
            try:
                return bool(is_done())
            except Exception:
                return False
        return False

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

        if not self._already_answered():
            self._used = True
            # Interaction responses expose no message object.
            try:
                await self.interaction.response.send_message(**kwargs)
                return None
            except discord.errors.InteractionResponded:
                # Somebody else answered first: continue as a follow-up.
                logger.debug("The interaction was already answered", exc_info=True)
        await self.interaction.followup.send(**kwargs)
        return None

    async def defer(self) -> None:
        """Acknowledge the interaction now, so long commands may take their time."""
        if not self._already_answered():
            self._used = True
            try:
                await self.interaction.response.defer()
            except discord.errors.InteractionResponded:
                logger.debug("The interaction was already answered", exc_info=True)

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
        if not self._already_answered():
            self._used = True
            try:
                await self.interaction.response.edit_message(**kwargs)
                return
            except discord.errors.InteractionResponded:
                logger.debug("The interaction was already answered", exc_info=True)
        await self.interaction.edit_original_response(**kwargs)


__all__ = ["PrefixResponder", "Responder", "SlashResponder"]

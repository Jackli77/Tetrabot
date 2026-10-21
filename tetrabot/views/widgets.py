"""Interactive Discord widgets.

These are the ``discord.ui`` views the bot attaches to its messages: the
duel-challenge buttons and the leaderboard pagination.  They only react to
interactions — all the rules live in the command logic and the models.
"""
from __future__ import annotations

import asyncio
import logging

import discord
from discord import ui

logger = logging.getLogger(__name__)

#: The reactions used to page through the leaderboard with ``!``.
PAGE_REACTIONS = ("⏮", "◀", "▶", "⏭")

#: How long the reaction-based pagination stays open, in seconds.
PAGINATION_TIMEOUT = 45.0


class ChallengeView(ui.View):
    """A "accept the duel" button.

    One class serves every duel: the label and the emoji are supplied by the
    caller, so the ``/gamble`` and ``/crit`` buttons can look different
    without duplicating the whole widget.
    """

    def __init__(
        self,
        challenger: discord.User,
        label: str = "Accepter le défi",
        emoji: str = "✅",
        style: discord.ButtonStyle = discord.ButtonStyle.success,
        timeout: float = 45.0,
    ):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.label = label
        self.emoji = emoji
        self.style = style
        self.accepted_by: discord.User | None = None

    @ui.button(label="Accepter le défi", emoji="✅", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        # Prevent the challenger from accepting their own challenge.
        if interaction.user.id == self.challenger.id:
            await interaction.response.send_message(
                "Tu ne peux pas parier contre toi-même !", ephemeral=True
            )
            return

        self.accepted_by = interaction.user
        button.disabled = True
        button.label = f"Accepté par {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        self.stop()


class LeaderboardPaginationView(ui.View):
    """Pagination buttons (first/prev/next/last) for the leaderboard embeds."""

    def __init__(self, pages: list[discord.Embed], author_id: int):
        super().__init__(timeout=90.0)
        self.pages = pages
        self.current_page = 0
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the command author may paginate the leaderboard."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Seule la personne ayant demandé le classement peut changer de page.",
                ephemeral=True,
            )
            return False
        return True

    async def _show(self, interaction: discord.Interaction, index: int) -> None:
        self.current_page = max(0, min(index, len(self.pages) - 1))
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @ui.button(emoji="⏮", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: ui.Button):
        """Jump to the first page."""
        await self._show(interaction, 0)

    @ui.button(emoji="◀", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: ui.Button):
        """Go to the previous page."""
        await self._show(interaction, self.current_page - 1)

    @ui.button(emoji="▶", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        """Go to the next page."""
        await self._show(interaction, self.current_page + 1)

    @ui.button(emoji="⏭", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: ui.Button):
        """Jump to the last page."""
        await self._show(interaction, len(self.pages) - 1)


async def paginate_with_reactions(
    message,
    client: discord.Client,
    pages: list[discord.Embed],
) -> None:
    """Page through embeds with ⏮ ◀ ▶ ⏭ reactions on a plain message.

    This is the ``!`` flavour of the leaderboard: the slash transport uses
    :class:`LeaderboardPaginationView` buttons instead.

    ``client`` is passed in explicitly: a :class:`discord.Message` has no
    ``client`` attribute, and the bot client is what owns ``wait_for``.
    """
    msg = await message.channel.send(embed=pages[0])
    for emoji in PAGE_REACTIONS:
        await msg.add_reaction(emoji)

    index = 0

    def check(reaction, user):
        return (
            reaction.emoji in PAGE_REACTIONS
            and reaction.message == msg
            and not user.bot
        )

    while True:
        try:
            reaction, user = await client.wait_for(
                "reaction_add", timeout=PAGINATION_TIMEOUT, check=check
            )
        except asyncio.TimeoutError:
            await msg.clear_reactions()
            return

        # Clean up the user's reaction after processing.
        if user != client.user:
            await msg.remove_reaction(reaction, user)

        emoji = str(reaction.emoji)
        if emoji == "⏮":
            index = 0
        elif emoji == "◀" and index > 0:
            index -= 1
        elif emoji == "▶" and index < len(pages) - 1:
            index += 1
        elif emoji == "⏭":
            index = len(pages) - 1
        await msg.edit(embed=pages[index])


__all__ = [
    "PAGE_REACTIONS",
    "PAGINATION_TIMEOUT",
    "ChallengeView",
    "LeaderboardPaginationView",
    "paginate_with_reactions",
]

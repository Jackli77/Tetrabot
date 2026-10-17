import discord
from discord import ui


# --- UI View for /incscore and /leaderboard ---
# Provides pagination buttons (first/prev/next/last) for leaderboard embeds.
class LeaderboardPaginationView(ui.View):
    def __init__(self, pages: list[discord.Embed], author_id: int):
        super().__init__(timeout=90.0)
        self.pages = pages
        self.current_page = 0
        self.author_id = author_id

    # Only the command author may paginate the leaderboard.
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Seule la personne ayant demandé le classement peut changer de page.", ephemeral=True)
            return False
        return True

    # Jump to the first page.
    @ui.button(emoji="⏮", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = 0
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    # Go to the previous page.
    @ui.button(emoji="◀", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    # Go to the next page.
    @ui.button(emoji="▶", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    # Jump to the last page.
    @ui.button(emoji="⏭", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = len(self.pages) - 1
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

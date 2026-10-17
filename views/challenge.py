import discord
from discord import ui


# --- UI View for /gamble challenge button ---
# Shows an "Accepter le Gamble" button that lets another user accept a gamble duel.
class GambleChallengeView(ui.View):
    def __init__(self, challenger: discord.User, upper: int, client: discord.Client):
        super().__init__(timeout=45.0)
        self.challenger = challenger        # User who initiated the gamble
        self.upper = upper                  # Maximum roll value
        self.client = client                # Discord bot client
        self.accepted_by: discord.User | None = None  # User who accepted the challenge

    # Button callback: records the acceptor and stops the view.
    @ui.button(label="Accepter le Gamble", emoji="🎲", style=discord.ButtonStyle.success)
    async def accept_gamble(self, interaction: discord.Interaction, button: ui.Button):
        # Prevent the challenger from accepting their own challenge.
        if interaction.user.id == self.challenger.id:
            await interaction.response.send_message("Tu ne peux pas parier contre toi-même !", ephemeral=True)
            return

        self.accepted_by = interaction.user
        button.disabled = True
        button.label = f"Accepté par {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        self.stop()


# --- UI View for /crit challenge button ---
# Shows an "Accepter le Crit" button that lets another user accept a critical-hit duel.
class CritChallengeView(ui.View):
    def __init__(self, challenger: discord.User, argent: int, client: discord.Client):
        super().__init__(timeout=45.0)
        self.challenger = challenger        # User who initiated the crit duel
        self.argent = argent                # Stake amount
        self.client = client                # Discord bot client
        self.accepted_by: discord.User | None = None  # User who accepted the challenge

    # Button callback: records the acceptor and stops the view.
    @ui.button(label="Accepter le Crit", emoji="⚡", style=discord.ButtonStyle.danger)
    async def accept_crit(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id == self.challenger.id:
            await interaction.response.send_message("Tu ne peux pas te défier toi-même !", ephemeral=True)
            return

        self.accepted_by = interaction.user
        button.disabled = True
        button.label = f"Accepté par {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        self.stop()

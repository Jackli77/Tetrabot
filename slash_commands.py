import asyncio
import random
from asyncio import sleep
import discord
from discord import app_commands, ui
import settings
from message_handler import COMMAND_HANDLERS
from dms_handler import DMS_HANDLERS
from database_init import users
from commands.incdb import incdb, winrate


# --- UI View for /incscore and /leaderboard ---
class LeaderboardPaginationView(ui.View):
    def __init__(self, pages: list[discord.Embed], author_id: int):
        super().__init__(timeout=90.0)
        self.pages = pages
        self.current_page = 0
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Seule la personne ayant demandé le classement peut changer de page.", ephemeral=True)
            return False
        return True

    @ui.button(emoji="⏮", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = 0
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @ui.button(emoji="◀", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @ui.button(emoji="▶", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @ui.button(emoji="⏭", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = len(self.pages) - 1
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)


# --- UI View for /gamble challenge button ---
class GambleChallengeView(ui.View):
    def __init__(self, challenger: discord.User, upper: int, client: discord.Client):
        super().__init__(timeout=45.0)
        self.challenger = challenger
        self.upper = upper
        self.client = client
        self.accepted_by: discord.User | None = None

    @ui.button(label="Accepter le Gamble", emoji="🎲", style=discord.ButtonStyle.success)
    async def accept_gamble(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id == self.challenger.id:
            await interaction.response.send_message("Tu ne peux pas parier contre toi-même !", ephemeral=True)
            return

        self.accepted_by = interaction.user
        button.disabled = True
        button.label = f"Accepté par {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        self.stop()


# --- UI View for /crit challenge button ---
class CritChallengeView(ui.View):
    def __init__(self, challenger: discord.User, argent: int, client: discord.Client):
        super().__init__(timeout=45.0)
        self.challenger = challenger
        self.argent = argent
        self.client = client
        self.accepted_by: discord.User | None = None

    @ui.button(label="Accepter le Crit", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def accept_crit(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id == self.challenger.id:
            await interaction.response.send_message("Tu ne peux pas te défier toi-même !", ephemeral=True)
            return

        self.accepted_by = interaction.user
        button.disabled = True
        button.label = f"Accepté par {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        self.stop()


def setup_slash_commands(bot: discord.Client, tree: app_commands.CommandTree):
    """Register integrated Discord native slash commands into the bot tree."""

    # 1. /commands
    @tree.command(name="commands", description="Affiche la liste interactive de toutes les commandes disponibles")
    async def cmd_commands(interaction: discord.Interaction):
        embed = discord.Embed(
            title="📜 Commandes disponibles",
            description=f"Le bot supporte les **Slash Commands** (`/`) et l'ancien préfixe texte (`{settings.COMMAND_PREFIX}`).",
            colour=discord.Colour.blue()
        )

        seen_cmds = set()
        server_lines = []
        for name, cmd in sorted(COMMAND_HANDLERS.items()):
            if cmd in seen_cmds:
                continue
            seen_cmds.add(cmd)

            param_str = " " + " ".join(f"<{p}>" for p in cmd.params) if cmd.params else ""
            cmd_signature = f"`/{cmd.name}{param_str}` ou `{settings.COMMAND_PREFIX}{cmd.name}`"
            if getattr(cmd, "aliases", None):
                alias_str = ", ".join(f"`{a}`" for a in cmd.aliases)
                cmd_signature += f" *(alias: {alias_str})*"

            desc = cmd.description
            if ": " in desc:
                desc = desc.split(": ", 1)[1]
            desc = desc.rstrip(".")

            server_lines.append(f"{cmd_signature}\n↳ {desc}")

        if server_lines:
            embed.add_field(
                name="💬 Commandes de serveur",
                value="\n\n".join(server_lines),
                inline=False
            )

        seen_dms = set()
        dm_lines = []
        for name, cmd in sorted(DMS_HANDLERS.items()):
            if cmd in seen_dms:
                continue
            seen_dms.add(cmd)

            param_str = " " + " ".join(f"<{p}>" for p in cmd.params) if cmd.params else ""
            cmd_signature = f"`/{cmd.name}{param_str}` ou `{settings.COMMAND_PREFIX}{cmd.name}`"

            desc = cmd.description
            if ": " in desc:
                desc = desc.split(": ", 1)[1]
            desc = desc.rstrip(".")

            dm_lines.append(f"{cmd_signature}\n↳ {desc}")

        if dm_lines:
            embed.add_field(
                name="📩 Commandes en message privé (DM)",
                value="\n\n".join(dm_lines),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # 2. /gamble
    @tree.command(name="gamble", description="Challenge un joueur à un gamble cappé à une somme maximale")
    @app_commands.describe(limite="Somme maximale de la roulette (ex: 100)")
    async def cmd_gamble(interaction: discord.Interaction, limite: app_commands.Range[int, 1, None]):
        challenger = interaction.user
        view = GambleChallengeView(challenger=challenger, upper=limite, client=bot)

        embed = discord.Embed(
            title="🎲 Duel Gamble",
            description=f"**{challenger.mention}** lance un gamble cappé à **{limite}** kakeras !\nCliquez ci-dessous pour accepter le défi.",
            colour=discord.Colour.gold()
        )
        await interaction.response.send_message(embed=embed, view=view)

        # Wait for user click or timeout
        await view.wait()
        channel = interaction.channel

        if not view.accepted_by:
            await channel.send("⏱️ Gamble annulé (personne n'a accepté dans le temps imparti).")
            return

        adv_usr = view.accepted_by
        lower = 1
        rolled1 = random.randint(lower, limite)
        rolled2 = random.randint(lower, limite)

        msg1 = f"🎲 {challenger.mention} vs {adv_usr.mention}. La roulette va de **{lower}** à **{limite}** 🎲"
        msg2 = f"🎲 La roulette donne **{rolled1}** pour **{challenger.display_name}** 🎲"
        msg3 = f"🎲 La roulette donne **{rolled2}** pour **{adv_usr.display_name}** 🎲"

        if rolled1 < rolled2:
            gain = rolled2 - rolled1
            msg4 = f"🏆 Le gagnant est **{challenger.display_name}** ! **{adv_usr.display_name}** lui doit **{gain}** kakeras !"
        elif rolled2 < rolled1:
            gain = rolled1 - rolled2
            msg4 = f"🏆 Le gagnant est **{adv_usr.display_name}** ! **{challenger.display_name}** lui doit **{gain}** kakeras !"
        else:
            msg4 = "⚖️ Égalité ! Pas de gagnant."

        await channel.send(msg1)
        await sleep(1.5)
        await channel.send(msg2)
        await sleep(1.5)
        await channel.send(msg3)
        await sleep(1.5)
        await channel.send(msg4)

        rec1 = await incdb(challenger.id, rolled2 - rolled1)
        rec2 = await incdb(adv_usr.id, rolled1 - rolled2)
        await channel.send(f"📊 **{challenger.display_name}** — Score: **{rec1[0][0]}**, Équité: **{rec1[0][1]}**")
        await channel.send(f"📊 **{adv_usr.display_name}** — Score: **{rec2[0][0]}**, Équité: **{rec2[0][1]}**")

    # 3. /crit
    @tree.command(name="crit", description="Lance un duel de coups critiques (chafer)")
    @app_commands.describe(somme="Mise initiale en jeu", odds="Pourcentage de chance de crit (10 à 90, défaut: 15)")
    async def cmd_crit(interaction: discord.Interaction, somme: app_commands.Range[int, 1, None], odds: app_commands.Range[int, 10, 90] = 15):
        challenger = interaction.user
        view = CritChallengeView(challenger=challenger, argent=somme, client=bot)

        embed = discord.Embed(
            title="⚔️ Duel de Chafer Crit",
            description=f"**{challenger.mention}** mise **{somme}** avec **{odds}%** de chance de crit !\nCliquez ci-dessous pour relever le défi.",
            colour=discord.Colour.red()
        )
        await interaction.response.send_message(embed=embed, view=view)

        await view.wait()
        channel = interaction.channel

        if not view.accepted_by:
            await channel.send("⏱️ Duel annulé (personne n'a accepté dans le temps imparti).")
            return

        adv_usr = view.accepted_by
        crit1 = 0
        crit2 = 0
        manche = 0
        argent = somme

        while crit1 == crit2:
            manche += 1
            await channel.send(f"__**Manche {manche}**__")
            await sleep(1)

            crited1 = random.randint(0, 100) < odds
            if crited1:
                crit1 += 1
                await channel.send(f"💥 **{challenger.display_name}** Coup critique !")
            else:
                await channel.send(f"💨 Pas de chance, **{challenger.display_name}**")

            await sleep(1)
            crited2 = random.randint(0, 100) < odds
            if crited2:
                crit2 += 1
                await channel.send(f"💥 **{adv_usr.display_name}** Coup critique !")
                if crited1:
                    argent *= 2
                    await channel.send(f"💸 Double crit ! La somme en jeu passe à **{argent}** !")
            else:
                await channel.send(f"💨 Pas de chance, **{adv_usr.display_name}**")

            await sleep(1)

        msg_end = f"Le duel s'est terminé après **{manche}** manches."
        if crit1 > crit2:
            winner, loser = challenger, adv_usr
            rec1 = await incdb(challenger.id, argent)
            rec2 = await incdb(adv_usr.id, -argent)
        else:
            winner, loser = adv_usr, challenger
            rec1 = await incdb(challenger.id, -argent)
            rec2 = await incdb(adv_usr.id, argent)

        await channel.send(f"{msg_end}\n🏆 **{winner.display_name}** l'emporte ! **{loser.display_name}** doit lui donner **{argent}** !")
        await channel.send(f"📊 **{challenger.display_name}** — Score: **{rec1[0][0]}**, Équité: **{rec1[0][1]}**")
        await channel.send(f"📊 **{adv_usr.display_name}** — Score: **{rec2[0][0]}**, Équité: **{rec2[0][1]}**")

    # Helper function for leaderboard rendering
    async def build_leaderboard_pages(interaction_user_id: int):
        records = await users.find().sort("equity", -1).to_list(length=None)
        if not records:
            return None, None

        page1 = discord.Embed(title="🏆 Classement d'équité", colour=discord.Colour.lighter_grey())
        top_usr = await bot.fetch_user(records[0]["_id"])
        page1.set_thumbnail(url=top_usr.display_avatar.url)
        page1.add_field(
            name="Membres",
            value="\n ".join(
                f"**{r.get('username', str(r['_id']))}** — "
                f"**WR:** {r.get('win', 0)}/{r.get('loss', 0)} ({winrate(r.get('win', 0), r.get('loss', 0))}%) — "
                f"**Équité:** {r.get('equity', 0)}"
                for r in records
            ),
            inline=False
        )

        page2 = discord.Embed(
            title="🥇 Grand gagnant",
            description=(
                f"**{records[0].get('username', str(records[0]['_id']))}** avec une équité de "
                f"**{records[0].get('equity', 0)}** et un winrate de "
                f"**{records[0].get('win', 0)}/{records[0].get('loss', 0)} "
                f"({winrate(records[0].get('win', 0), records[0].get('loss', 0))}%)**"
            ),
            colour=discord.Colour.green()
        )
        page2.set_thumbnail(url=top_usr.display_avatar.url)

        bot_usr = await bot.fetch_user(records[-1]["_id"])
        page3 = discord.Embed(
            title="💀 Grand perdant",
            description=(
                f"**{records[-1].get('username', str(records[-1]['_id']))}** avec une équité de "
                f"**{records[-1].get('equity', 0)}** et un winrate de "
                f"**{records[-1].get('win', 0)}/{records[-1].get('loss', 0)} "
                f"({winrate(records[-1].get('win', 0), records[-1].get('loss', 0))}%)**"
            ),
            colour=discord.Colour.red()
        )
        page3.set_thumbnail(url=bot_usr.display_avatar.url)

        pages = [page1, page2, page3]
        view = LeaderboardPaginationView(pages=pages, author_id=interaction_user_id)
        return pages, view

    # 4. /incscore & 5. /leaderboard
    @tree.command(name="incscore", description="Affiche le classement des joueurs par équité avec boutons interactifs")
    async def cmd_incscore(interaction: discord.Interaction):
        pages, view = await build_leaderboard_pages(interaction.user.id)
        if not pages:
            await interaction.response.send_message("Aucun joueur enregistré dans la base de données.", ephemeral=True)
            return
        await interaction.response.send_message(embed=pages[0], view=view)

    @tree.command(name="leaderboard", description="Affiche le classement des joueurs par équité avec boutons interactifs")
    async def cmd_leaderboard(interaction: discord.Interaction):
        pages, view = await build_leaderboard_pages(interaction.user.id)
        if not pages:
            await interaction.response.send_message("Aucun joueur enregistré dans la base de données.", ephemeral=True)
            return
        await interaction.response.send_message(embed=pages[0], view=view)

    # 6. /random
    @tree.command(name="random", description="Tire un nombre aléatoire entre deux bornes")
    @app_commands.describe(min="Borne minimale (défaut: 1)", max="Borne maximale (défaut: 100)")
    async def cmd_random(interaction: discord.Interaction, min: int = 1, max: int = 100):
        if min > max:
            await interaction.response.send_message("La borne minimale ne peut pas être supérieure à la borne maximale !", ephemeral=True)
            return
        rolled = random.randint(min, max)
        embed = discord.Embed(
            title="🎲 Tirage Aléatoire",
            description=f"Intervalle : **{min}** à **{max}**\n\n🎯 Résultat : **{rolled}**",
            colour=discord.Colour.purple()
        )
        await interaction.response.send_message(embed=embed)

    # 7. /exo
    @tree.command(name="exo", description="Simule le bénéfice ou la perte sur une tentative d'exo")
    @app_commands.describe(prix="Prix d'une tentative en kamas (défaut: 30000)")
    async def cmd_exo(interaction: discord.Interaction, prix: int = 30000):
        c = 1
        rep = random.randint(1, 100)
        r = random.randint(1, 100)
        while r != rep:
            c += 1
            r = random.randint(1, 100)

        if c <= 100:
            benef = prix * (100 - c)
            formatted = f"{benef:,}".replace(",", " ")
            desc = f"**{c}** tentative(s) avant l'exo !\n💰 Bénéfice : **{formatted} kamas**"
            colour = discord.Colour.green()
        else:
            perte = prix * (c - 100)
            formatted = f"{perte:,}".replace(",", " ")
            desc = f"**{c}** tentatives avant l'exo...\n📉 Perte : **{formatted} kamas**"
            colour = discord.Colour.red()

        embed = discord.Embed(title="⚒️ Simulation Exo", description=desc, colour=colour)
        await interaction.response.send_message(embed=embed)

    # 8. /clean
    @tree.command(name="clean", description="Supprime un nombre donné de messages dans ce salon")
    @app_commands.describe(nombre="Nombre de messages à supprimer (1 à 100)")
    async def cmd_clean(interaction: discord.Interaction, nombre: app_commands.Range[int, 1, 100]):
        # Deferred response to avoid interaction timeout while deleting
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=nombre)
        await interaction.followup.send(f"🧹 **{len(deleted)}** message(s) supprimé(s).", ephemeral=True)

    # 9. /aup
    @tree.command(name="aup", description="Fais venir quelqu'un au pied")
    @app_commands.describe(cible="Membre ou texte à appeler")
    async def cmd_aup(interaction: discord.Interaction, cible: str):
        await interaction.response.send_message(f"Au pied, {cible} ! <:bontoutou:790992228301668352>")
        await sleep(2)
        for _ in range(3):
            await interaction.channel.send(f"Viens ici {cible} et fais waf <:bontoutou:790992228301668352>")
            await sleep(1)

    # 10. /inc
    @tree.command(name="inc", description="Incrémente ton score et affiche tes statistiques")
    async def cmd_inc(interaction: discord.Interaction):
        records = await incdb(interaction.user.id, 0)
        wr = winrate(records[0][2], records[0][3])
        embed = discord.Embed(
            title=f"📈 Statistiques de {interaction.user.display_name}",
            colour=discord.Colour.blue()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Parties jouées", value=str(records[0][0]), inline=True)
        embed.add_field(name="Équité nette", value=str(records[0][1]), inline=True)
        embed.add_field(name="Winrate", value=f"{records[0][2]}W / {records[0][3]}L ({wr}%)", inline=True)
        await interaction.response.send_message(embed=embed)

    # 11. /fh
    @tree.command(name="fh", description="Fuck qui ?")
    async def cmd_fh(interaction: discord.Interaction):
        await interaction.response.send_message("Fuck qui ?\nFuck hugo !")

    # 12. /rig
    @tree.command(name="rig", description="Truque les jeux d'argent")
    async def cmd_rig(interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ **{interaction.user.display_name}**, the games have been successfully rigged.")

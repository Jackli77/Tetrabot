"""DETECTOR/``/``: recognise native slash invocations on the command tree.

:class:`SlashDetector` registers all Discord slash (app) commands on the
bot's command tree.  Every command is a thin detector: it builds a shared
:class:`controllers.CommandContext` (see :mod:`controllers.context`) and
dispatches to the SAME ``controllers.LOGIC`` functions the ``!`` detector
uses.  Interactive UI widgets (challenge buttons, leaderboard pagination)
live in the :mod:`views` package.
"""
import discord
from discord import app_commands

from controllers import LOGIC, CommandContext, make_slash_respond
from detectors.base import BaseDetector, DetectionResult
from views.challenge import CritChallengeView, GambleChallengeView
from views.leaderboard import LeaderboardPaginationView


def build_context(interaction: discord.Interaction, args=None) -> CommandContext:
    """Build the shared :class:`CommandContext` for a slash command."""
    return CommandContext(
        author=interaction.user,
        channel=interaction.channel,
        client=interaction.client,
        args=list(args or []),
        respond=make_slash_respond(interaction),
        prefix="/",
    )


class SlashDetector(BaseDetector):
    """Detect ``/`` invocations by registering the slash tree.

    Detection for slash commands happens inside Discord itself (the user
    picks a registered command); this class only wires the tree so every
    invocation normalises into a :class:`CommandContext` and reaches the
    shared logic.  :meth:`detect` therefore always reports ``handled=True``
    with no command/args (dispatch already happened in the tree callback).
    """

    name = "/"

    def __init__(self, bot: discord.Client | None = None):
        self.bot = bot

    async def detect(self, interaction: discord.Interaction, bot_client=None) -> DetectionResult:
        """Slash invocations always dispatch via the tree — nothing to parse."""
        return DetectionResult(handled=True, extra={"slash": True})

    def setup(self, bot: discord.Client, tree: app_commands.CommandTree):
        """Register every slash command on ``tree`` (thin LOGIC wrappers)."""
        self.bot = bot
        setup_slash_commands(bot, tree)
        return tree


def setup_slash_commands(bot: discord.Client, tree: app_commands.CommandTree):
    """Register integrated Discord native slash commands into the bot tree.

    Each command below is a thin detector: it builds the shared
    CommandContext and dispatches to ``controllers.LOGIC`` so that the slash
    and prefix variants run the exact same code.
    """

    # 1. /commands — Lists all available server and DM commands in an embed.
    @tree.command(name="commands", description="Affiche la liste interactive de toutes les commandes disponibles")
    async def cmd_commands(interaction: discord.Interaction):
        ctx = build_context(interaction)
        await LOGIC["cmd_help"](ctx)

    # 2. /gamble — Starts a gamble duel with another user via a button challenge.
    @tree.command(name="gamble", description="Challenge un joueur à un gamble cappé à une somme maximale")
    @app_commands.describe(limite="Somme maximale de la roulette (ex: 100)")
    async def cmd_gamble(interaction: discord.Interaction, limite: app_commands.Range[int, 1, None]):
        challenger = interaction.user
        view = GambleChallengeView(challenger=challenger, upper=limite, client=bot)
        ctx = build_context(interaction)

        embed = discord.Embed(
            title="🎲 Duel Gamble",
            description=f"**{challenger.mention}** lance un gamble cappé à **{limite}** kakeras !\nCliquez ci-dessous pour accepter le défi.",
            colour=discord.Colour.gold(),
        )
        await ctx.respond(embed=embed, view=view)

        # Wait for the accept button click or a timeout.
        await view.wait()

        if not view.accepted_by:
            await interaction.channel.send("⏱️ Gamble annulé (personne n'a accepté dans le temps imparti).")
            return

        # Shared duel logic takes over from here.
        await LOGIC["cmd_gamble"](ctx, view.accepted_by, limite)



    # 3. /crit — Starts a critical-hit duel with another user via a button challenge.
    @tree.command(name="crit", description="Lance un duel de coups critiques (chafer)")
    @app_commands.describe(somme="Mise initiale en jeu", odds="Pourcentage de chance de crit (10 à 90, défaut: 15)")
    async def cmd_crit(interaction: discord.Interaction, somme: app_commands.Range[int, 1, None], odds: app_commands.Range[int, 10, 90] = 15):
        challenger = interaction.user
        view = CritChallengeView(challenger=challenger, argent=somme, client=bot)
        ctx = build_context(interaction)

        embed = discord.Embed(
            title="⚡ Duel Crit",
            description=f"**{challenger.mention}** mise **{somme}** avec **{odds}%** de chance de crit !\nCliquez ci-dessous pour relever le défi.",
            colour=discord.Colour.red(),
        )
        await ctx.respond(embed=embed, view=view)

        await view.wait()

        if not view.accepted_by:
            await interaction.channel.send("⏱️ Duel annulé (personne n'a accepté dans le temps imparti).")
            return

        # Shared duel logic takes over from here.
        await LOGIC["cmd_crit"](ctx, view.accepted_by, somme, odds)

    # Helper shared by /incscore and /leaderboard: the embed pages come from
    # controllers.commands.cmd_incscore, while the pagination buttons stay in the view.
    async def send_leaderboard(interaction: discord.Interaction):
        pages = await LOGIC["cmd_incscore"](build_context(interaction))
        if not pages:
            await interaction.response.send_message("Aucun joueur enregistré dans la base de données.", ephemeral=True)
            return
        view = LeaderboardPaginationView(pages=pages, author_id=interaction.user.id)
        await interaction.response.send_message(embed=pages[0], view=view)

    # 4. /incscore — Shows the equity leaderboard with interactive pagination buttons.
    @tree.command(name="incscore", description="Affiche le classement des joueurs par équité avec boutons interactifs")
    async def cmd_incscore(interaction: discord.Interaction):
        await send_leaderboard(interaction)

    # 5. /leaderboard — Alias for /incscore, shows the same leaderboard.
    @tree.command(name="leaderboard", description="Affiche le classement des joueurs par équité avec boutons interactifs")
    async def cmd_leaderboard(interaction: discord.Interaction):
        await send_leaderboard(interaction)

    # 6. /random — Rolls a random number between min and max (default 1 to 100).
    @tree.command(name="random", description="Tire un nombre aléatoire entre deux bornes")
    @app_commands.describe(min="Borne minimale (défaut: 1)", max="Borne maximale (défaut: 100)")
    async def cmd_random(interaction: discord.Interaction, min: int = 1, max: int = 100):
        ctx = build_context(interaction, args=[str(min), str(max)])
        await LOGIC["cmd_random"](ctx)

    # 7. /clean — Deletes a given number of recent messages in the channel.
    @tree.command(name="clean", description="Supprime un nombre donné de messages dans ce salon")
    @app_commands.describe(nombre="Nombre de messages à supprimer (1 à 100)")
    async def cmd_clean(interaction: discord.Interaction, nombre: app_commands.Range[int, 1, 100]):
        ctx = build_context(interaction, args=[str(nombre)])
        # A slash invocation has no command message to clean up, and the final
        # confirmation should only be visible to the invoker.
        ctx.extra["slash"] = True
        ctx._ephemeral = True
        await LOGIC["cmd_clean"](ctx)

    # 8. /aup — Pings a target and repeatedly asks them to come ("au pied").
    @tree.command(name="aup", description="Fais venir quelqu'un au pied")
    @app_commands.describe(cible="Membre ou texte à appeler")
    async def cmd_aup(interaction: discord.Interaction, cible: str):
        ctx = build_context(interaction, args=[cible])
        await LOGIC["cmd_aup"](ctx)

    # 9. /inc — Displays the user's current stats (games played, equity, winrate).
    @tree.command(name="inc", description="Incrémente ton score et affiche tes statistiques")
    async def cmd_inc(interaction: discord.Interaction):
        ctx = build_context(interaction)
        await LOGIC["cmd_inc"](ctx)

    # 10. /chat — Forwards the user's message to the local Ollama LLM (qwen3:4b)
    # and replies in the channel with the generated answer.
    @tree.command(name="chat", description="Envoie ton message au chatbot local (Ollama) et affiche sa réponse")
    @app_commands.describe(message="Le message à envoyer au chatbot")
    async def cmd_chat(interaction: discord.Interaction, message: str):
        ctx = build_context(interaction, args=[message])
        await LOGIC["cmd_chat"](ctx)

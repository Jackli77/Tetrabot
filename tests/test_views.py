"""Pure unit tests for the view renderers (no I/O, no database)."""
from __future__ import annotations

import asyncio

import discord
import pytest

from tetrabot import catalog
from tetrabot.models.stats import Stats
from tetrabot.views import formatting as fmt
from tetrabot.views.widgets import paginate_with_reactions


class TestSimpleStrings:
    def test_render_stats(self):
        stats = Stats(user_id=1, val=7, equity=-30, win=1, loss=3, username="alice")
        assert fmt.render_stats("Bob", stats) == (
            "**Bob** score:**7** équité:**-30** WR:**1/3 25%**"
        )

    def test_render_score(self):
        stats = Stats(user_id=1, val=7, equity=-30, win=1, loss=3, username="alice")
        assert fmt.render_score("Bob", stats) == (
            "**Bob** a un score de **7** et une équité de **-30**"
        )

    def test_render_roulette(self):
        out = fmt.render_roulette("Bob", 1, 100, 57)
        assert "La mère d'Hugo vient de tirer un **57**! **Bob**" in out

    def test_render_aup(self):
        assert fmt.render_aup_call("@a") == f"Au pièd,@a {fmt.TOUTOU}"
        assert fmt.render_aup_urge("@a") == f"Viens ici @a et fais waf {fmt.TOUTOU}"


class TestGambleRendering:
    def test_render_intro(self):
        intro = fmt.render_gamble_intro("<@1>", "<@2>", 1, 10)
        assert "<@1> vs <@2>" in intro
        assert "**10**" in intro

    def test_render_roll(self):
        assert fmt.render_gamble_roll("Bob", 4) == f"{fmt.DIE} Bob a tiré **4**! {fmt.DIE}"

    def test_render_tie(self):
        assert fmt.render_gamble_tie() == f"{fmt.CHEEMS} égalité pas de gagnant {fmt.CHEEMS}"

    def test_decisive_win_wording(self):
        out = fmt.render_gamble_winner("W", "L", 5, True)
        assert "s'est bien fait baiser et doit **5**" in out

    def test_close_win_wording(self):
        out = fmt.render_gamble_winner("W", "L", 1, False)
        assert " doit **1**" in out
        assert "baiser" not in out


class TestCritRendering:
    def test_render_round(self):
        assert fmt.render_crit_round(3) == "__**Manche 3**__"

    def test_render_hit(self):
        assert fmt.render_crit_hit("Bob") == f"**Bob** Coup critique!{fmt.BANG}"

    def test_render_miss(self):
        assert fmt.render_crit_miss("Bob") == f"Pas de chance, **Bob** {fmt.CHEEMS}"

    def test_render_escalation(self):
        assert fmt.render_crit_escalation(40) == (
            f"La somme en jeu passe à **40** {fmt.MONEY_WINGS}"
        )

    def test_render_outcome(self):
        outcome = fmt.render_crit_outcome(4, 1, "W", "L", 40)
        assert outcome.splitlines()[0] == (
            "Le duel s'est terminé après **4** manches et **1** égalités"
        )
        assert "**W**, **L** doit donner **40**" in outcome


class TestSharedControllerReplies:
    """The renderers the controllers use for their own replies."""

    def test_render_missing_arguments(self):
        assert fmt.render_missing_arguments("<@1>", 1) == (
            "<@1> Cette fonction à besoin de minimum 1 arguments"
        )

    def test_render_challenge_embed(self):
        embed = fmt.render_challenge_embed("🎲 Duel Gamble", "**<@1>** lance un gamble")
        assert embed.title == "🎲 Duel Gamble"
        assert embed.description == "**<@1>** lance un gamble"
        assert embed.colour == discord.Colour.gold()


class TestHelpEmbed:
    def test_embed_has_one_field_per_group(self):
        embed = fmt.render_help("!")
        assert embed.title == "📝 Commandes disponibles"
        assert len(embed.fields) == 2
        assert embed.fields[0].name == "💬 Commandes de serveur"
        assert embed.fields[1].name == "📩 Commandes en message privé (DM)"

    def test_command_line_shows_usage(self):
        spec = catalog.find("clean")
        line = fmt.command_line("!", spec)
        assert "`!clean <nombre>`" in line
        assert "*(alias: `!c`)*" in line

    def test_command_line_shows_optional_params(self):
        spec = catalog.find("random")
        line = fmt.command_line("!", spec)
        assert "`!random [min] [max]`" in line

    def test_aliases_are_not_listed_as_commands(self):
        """Aliases appear as annotations, never as their own command line."""
        embed = fmt.render_help("!")
        guild_field = embed.fields[0].value
        lines = guild_field.splitlines()

        assert "`!clean <nombre>`" in guild_field
        assert "`!incscore`" in guild_field
        # The alias is mentioned, but only inside the annotation.
        assert any("`!c`" in line for line in lines)
        assert not any(line.startswith("`!c`") for line in lines)
        assert not any(line.startswith("`!lb`") for line in lines)


class TestLeaderboardPages:
    @pytest.fixture
    def records(self):
        return [
            Stats(user_id=1, val=10, equity=500, win=5, loss=1, username="top"),
            Stats(user_id=2, val=3, equity=-20, win=1, loss=2, username="mid"),
            Stats(user_id=3, val=9, equity=-999, win=0, loss=9, username="bottom"),
        ]

    def test_three_pages(self, records):
        pages = fmt.render_leaderboard_pages(records, "http://top", "http://bottom")
        assert len(pages) == 3

    def test_member_list(self, records):
        pages = fmt.render_leaderboard_pages(records, "http://top", "http://bottom")
        assert pages[0].title == "🏆 Classement d'équité"
        assert pages[0].fields[0].value == (
            "**top** — **WR:** 5/1 (83%) — **Équité:** 500\n "
            "**mid** — **WR:** 1/2 (33%) — **Équité:** -20\n "
            "**bottom** — **WR:** 0/9 (0%) — **Équité:** -999"
        )

    def test_thumbnails(self, records):
        pages = fmt.render_leaderboard_pages(records, "http://top", "http://bottom")
        assert pages[0].thumbnail.url == "http://top"
        assert pages[2].thumbnail.url == "http://bottom"

    def test_winner_and_loser_pages(self, records):
        pages = fmt.render_leaderboard_pages(records, "http://top", "http://bottom")
        assert pages[1].title == "🥇 Grand gagnant"
        assert "top" in pages[1].description
        assert pages[2].title == "💀 Grand perdant"
        assert "bottom" in pages[2].description


class _PaginatedMessage:
    """A message stand-in that deliberately has no ``client`` attribute.

    A real :class:`discord.Message` has no ``client`` either, so this keeps
    the pagination code honest.
    """

    def __init__(self):
        self.channel = _PaginatedChannel()
        self.edits = []


class _PaginatedChannel:
    def __init__(self):
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)
        return _PaginatedSentMessage()


class _PaginatedSentMessage:
    def __init__(self):
        self.reactions = []
        self.edits = []

    async def add_reaction(self, emoji):
        self.reactions.append(emoji)

    async def clear_reactions(self):
        self.reactions = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class _TimeoutClient:
    """A client whose ``wait_for`` always times out."""

    def __init__(self):
        self.user = "BOT"

    async def wait_for(self, event, timeout=None, check=None):
        raise asyncio.TimeoutError


class TestReactionPagination:
    def test_does_not_need_a_client_on_the_message(self):
        """The bot client must come from the caller, not from the message.

        A :class:`discord.Message` has no ``client`` attribute — reaching for
        one raises ``AttributeError`` at runtime.
        """
        message = _PaginatedMessage()
        client = _TimeoutClient()
        pages = fmt.render_leaderboard_pages(
            [
                Stats(user_id=1, equity=10, username="top"),
                Stats(user_id=2, equity=-5, username="bottom"),
            ],
            "http://top",
            "http://bottom",
        )

        assert not hasattr(message, "client")

        # Must not raise: the timeout path clears the reactions and returns.
        asyncio.run(paginate_with_reactions(message, client, pages))

        assert len(message.channel.sent) == 1
        assert message.channel.sent[0]["embed"] is pages[0]

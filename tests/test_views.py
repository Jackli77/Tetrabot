"""Pure unit tests for the view renderers (no I/O, no database)."""
from models.stats import Stats
from views import formatting as fmt


class FakeCommand:
    """Stands in for a BaseCommand instance (hashable, like the real ones)."""

    def __init__(self, name, params, aliases, description):
        self.name = name
        self.params = params
        self.aliases = aliases
        self.description = description


def run():
    die, cheems = fmt.DIE, fmt.CHEEMS

    # --- simple strings ----------------------------------------------------
    s = Stats(user_id=1, val=7, equity=-30, win=1, loss=3, username="alice")
    assert fmt.render_stats("Bob", s) == "**Bob** score:**7** équité:**-30** WR:**1/3 25%**"
    assert fmt.render_score("Bob", s) == "**Bob** a un score de **7** et une équité de **-30**"
    assert "La mère d'Hugo vient de tirer un **57**! **Bob**" in fmt.render_roulette("Bob", 1, 100, 57)

    assert fmt.render_aup_call("@a") == f"Au pièd,@a {fmt.TOUTOU}"
    assert fmt.render_aup_urge("@a") == f"Viens ici @a et fais waf {fmt.TOUTOU}"

    # --- gamble ------------------------------------------------------------
    intro = fmt.render_gamble_intro("<@1>", "<@2>", 1, 10)
    assert "<@1> vs <@2>" in intro and "**10**" in intro
    assert fmt.render_gamble_roll("Bob", 4) == f"{die} Bob a tiré **4**! {die}"
    assert fmt.render_gamble_tie() == f"{cheems} égalité pas de gagnant {cheems}"
    decisive_win = fmt.render_gamble_winner("W", "L", 5, True)
    assert "s'est bien fait baiser et doit **5**" in decisive_win
    close_win = fmt.render_gamble_winner("W", "L", 1, False)
    assert " doit **1**" in close_win and "baiser" not in close_win

    # --- crit --------------------------------------------------------------
    assert fmt.render_crit_round(3) == "__**Manche 3**__"
    assert fmt.render_crit_hit("Bob") == f"**Bob** Coup critique!{fmt.BANG}"
    assert fmt.render_crit_miss("Bob") == f"Pas de chance, **Bob** {cheems}"
    assert fmt.render_crit_escalation(40) == f"La somme en jeu passe à **40** {fmt.MONEY_WINGS}"
    outcome = fmt.render_crit_outcome(4, 1, "W", "L", 40)
    assert outcome.splitlines()[0] == "Le duel s'est terminé après **4** manches et **1** égalités"
    assert "**W**, **L** doit donner **40**" in outcome

    # --- help embed --------------------------------------------------------
    alpha = FakeCommand("alpha", ["user"], ["a"], "**!alpha** *<user>*: Does alpha stuff.")
    beta = FakeCommand("beta", [], [], "**!beta**: Does beta stuff.")
    # "alias-a" sorts before "alpha" — the canonical cmd.name must still win.
    server = {"alpha": alpha, "beta": beta, "alias-a": alpha}
    dms = {"beta": beta}

    embed = fmt.render_help("!", server, dms)
    assert embed.title == "📝 Commandes disponibles"
    assert len(embed.fields) == 2
    server_field, dm_field = embed.fields[0], embed.fields[1]
    assert server_field.name == "💬 Commandes de serveur"
    # Duplicated aliases share the same handler object -> rendered once.
    assert server_field.value.count("Does alpha stuff") == 1
    assert "`!alpha <user>`" in server_field.value
    assert "`!alias-a`" not in server_field.value
    assert "*(alias: `!a`)*" in server_field.value
    assert "`!beta`" in server_field.value
    assert dm_field.name == "📩 Commandes en message privé (DM)"
    assert "`!beta`" in dm_field.value

    # --- leaderboard pages -------------------------------------------------
    records = [
        Stats(user_id=1, val=10, equity=500, win=5, loss=1, username="top"),
        Stats(user_id=2, val=3, equity=-20, win=1, loss=2, username="mid"),
        Stats(user_id=3, val=9, equity=-999, win=0, loss=9, username="bottom"),
    ]
    pages = fmt.render_leaderboard_pages(records, "http://top", "http://bottom")
    assert len(pages) == 3
    assert pages[0].title == "🏆 Classement d'équité"
    assert pages[0].fields[0].value == (
        "**top** — **WR:** 5/1 (83%) — **Équité:** 500\n "
        "**mid** — **WR:** 1/2 (33%) — **Équité:** -20\n "
        "**bottom** — **WR:** 0/9 (0%) — **Équité:** -999"
    )
    assert pages[0].thumbnail.url == "http://top"
    assert pages[1].title == "🥇 Grand gagnant" and "top" in pages[1].description
    assert pages[2].title == "💀 Grand perdant" and "bottom" in pages[2].description
    assert pages[2].thumbnail.url == "http://bottom"

    print("test_views: all passed")

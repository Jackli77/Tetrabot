"""The command catalog — one declarative entry per command.

Each :class:`CommandSpec` describes a command *once*: its name, aliases,
description, parameters, and which shared handler (``handler``) serves it.
Both transports are generated from this catalog, so a command can never
exist on one transport only by accident:

* :mod:`tetrabot.controllers.prefix` builds the ``!`` router from it,
* :mod:`tetrabot.controllers.slash` builds the Discord ``/`` tree from it,
* :mod:`tetrabot.views.formatting` builds the help embed from it.

The catalog holds **data only** — no Discord imports, no behaviour.  The
shared implementations live in :mod:`tetrabot.controllers.commands`.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Scope(Enum):
    """Where a prefix command may be used."""

    GUILD = "guild"
    DM = "dm"
    BOTH = "both"

    @property
    def allows_guild(self) -> bool:
        return self in (Scope.GUILD, Scope.BOTH)

    @property
    def allows_dm(self) -> bool:
        return self in (Scope.DM, Scope.BOTH)


@dataclass(frozen=True)
class Param:
    """A single parameter of a command.

    ``required`` drives the prefix argument-count check and the way the
    parameter is shown in the help embed; ``type``/``minimum``/``maximum`` are
    used to build the matching Discord slash-command option.
    """

    name: str
    description: str = ""
    required: bool = True
    type: type = str
    default: object = None
    minimum: int | None = None
    maximum: int | None = None

    @property
    def display(self) -> str:
        """How the parameter is shown in the help embed."""
        return f"<{self.name}>" if self.required else f"[{self.name}]"


@dataclass(frozen=True)
class CommandSpec:
    """Everything the bot knows about a single command."""

    name: str
    description: str
    handler: str
    params: tuple[Param, ...] = ()
    aliases: tuple[str, ...] = ()
    scope: Scope = Scope.GUILD
    slash_names: tuple[str, ...] = ()
    slash_params: tuple[Param, ...] = ()
    expose_as_slash: bool = True
    ephemeral: bool = False
    needs_challenge: bool = False

    @property
    def names(self) -> tuple[str, ...]:
        """The command name plus every alias."""
        return (self.name,) + self.aliases

    @property
    def required_params(self) -> tuple[Param, ...]:
        """The parameters a caller must supply."""
        return tuple(p for p in self.params if p.required)

    @property
    def slash_name_list(self) -> tuple[str, ...]:
        """The names this command is registered under in the ``/`` tree."""
        return self.slash_names or (self.name,)

    def usage(self) -> str:
        """The parameter part of the command, e.g. ``<limite> [odds]``."""
        return " ".join(p.display for p in self.params)


COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec(
        name="inc",
        description="Incrémente ton score et affiche tes statistiques",
        handler="cmd_inc",
    ),
    CommandSpec(
        name="random",
        description=(
            "Donne un nombre aléatoire entre 1 et 100 "
            "(un seul argument est le maximum, deux arguments sont les bornes)"
        ),
        handler="cmd_random",
        params=(
            Param("min", "Borne minimale", required=False, type=int, default=1),
            Param("max", "Borne maximale", required=False, type=int, default=100),
        ),
        slash_params=(
            Param("min", "Borne minimale", required=False, type=int, default=1),
            Param("max", "Borne maximale", required=False, type=int, default=100),
        ),
    ),
    CommandSpec(
        name="aup",
        description="Fais venir quelqu'un au pied",
        handler="cmd_aup",
        params=(Param("@toutou", "Membre ou texte à appeler"),),
        slash_params=(Param("cible", "Membre ou texte à appeler"),),
    ),
    CommandSpec(
        name="clean",
        description="Supprime un nombre donné de messages",
        handler="cmd_clean",
        params=(Param("nombre", "Nombre de messages à supprimer (1 à 100)", type=int),),
        aliases=("c",),
        slash_params=(
            Param(
                "nombre",
                "Nombre de messages à supprimer (1 à 100)",
                type=int,
                minimum=1,
                maximum=100,
            ),
        ),
        ephemeral=True,
    ),
    CommandSpec(
        name="incscore",
        description="Affiche le classement (leaderboard) des joueurs par équité",
        handler="cmd_incscore",
        aliases=("leaderboard", "lb", "classement"),
        slash_names=("incscore", "leaderboard"),
    ),
    CommandSpec(
        name="commands",
        description="Affiche la liste de toutes les commandes disponibles",
        handler="cmd_help",
        scope=Scope.BOTH,
    ),
    CommandSpec(
        name="gamble",
        description="Challenge un joueur à un gamble",
        handler="cmd_gamble",
        params=(Param("limite", "Somme maximale de la roulette", type=int),),
        slash_params=(
            Param("limite", "Somme maximale de la roulette (ex: 100)", type=int, minimum=1),
        ),
        needs_challenge=True,
    ),
    CommandSpec(
        name="crit",
        description="Lance un crit avec la première personne qui réagit",
        handler="cmd_crit",
        params=(
            Param("somme", "Mise initiale en jeu", type=int),
            Param(
                "odds",
                "Pourcentage de chance de crit (10 à 90)",
                required=False,
                type=int,
                default=15,
            ),
        ),
        slash_params=(
            Param("somme", "Mise initiale en jeu", type=int, minimum=0),
            Param(
                "odds",
                "Pourcentage de chance de crit (10 à 90)",
                required=False,
                type=int,
                default=15,
                minimum=10,
                maximum=90,
            ),
        ),
        needs_challenge=True,
    ),
    CommandSpec(
        name="chat",
        description="Envoie ton message au chatbot local (Ollama) et affiche sa réponse",
        handler="cmd_chat",
        params=(Param("message", "Le message à envoyer au chatbot"),),
        slash_params=(Param("message", "Le message à envoyer au chatbot"),),
    ),
)


def find(name: str) -> CommandSpec | None:
    """Find a command by its name or by one of its aliases."""
    key = name.lower()
    for spec in COMMANDS:
        if key in spec.names:
            return spec
    return None


def guild_commands() -> tuple[CommandSpec, ...]:
    """The commands usable in a guild channel."""
    return tuple(spec for spec in COMMANDS if spec.scope.allows_guild)


def dm_commands() -> tuple[CommandSpec, ...]:
    """The commands usable in a private message."""
    return tuple(spec for spec in COMMANDS if spec.scope.allows_dm)


def slash_commands() -> tuple[CommandSpec, ...]:
    """The commands exposed in the ``/`` tree."""
    return tuple(spec for spec in COMMANDS if spec.expose_as_slash)


__all__ = [
    "COMMANDS",
    "CommandSpec",
    "Param",
    "Scope",
    "dm_commands",
    "find",
    "guild_commands",
    "slash_commands",
]


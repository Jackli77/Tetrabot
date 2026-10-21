"""Rendering for the chatbot.

The answer of a chatbot is not just text: how it is *presented* is a big
part of why it feels good to talk to it.  This module turns a raw model
answer into something that reads well in Discord:

* long answers become an **embed** instead of a wall of text,
* code blocks are extracted and shown in their own block with a language
  tag, which is what a programmer expects,
* the model is told to answer in the language of the conversation, and the
  answer keeps the personality of the bot.
"""
from __future__ import annotations

import re

import discord

#: Discord's message limit.
DISCORD_CHAR_LIMIT = 2000

#: The maximum length of an embed description.
EMBED_DESCRIPTION_LIMIT = 4096

#: A fenced code block, with or without a language.
CODE_BLOCK_RE = re.compile(r"```(\w*)\n?(.*?)```", re.DOTALL)

#: A language tag -> the Discord syntax highlighting keyword.
LANGUAGE_ALIASES = {
    "python": "python",
    "py": "python",
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "html": "html",
    "css": "css",
    "json": "json",
    "bash": "bash",
    "sh": "bash",
    "shell": "bash",
    "sql": "sql",
    "rust": "rust",
    "go": "go",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "yaml": "yaml",
    "yml": "yaml",
}


def split_code_blocks(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Split an answer into its prose and its code blocks.

    Returns ``(prose, blocks)`` where ``blocks`` is a list of
    ``(language, code)`` pairs.
    """
    blocks: list[tuple[str, str]] = []

    def _take(match: re.Match[str]) -> str:
        language = (match.group(1) or "").strip().lower()
        code = match.group(2).strip()
        blocks.append((language, code))
        return "\n"

    prose = CODE_BLOCK_RE.sub(_take, text)
    return prose.strip(), blocks


def _embed_colour() -> discord.Colour:
    """The colour of the chat embed."""
    return discord.Colour.blurple()


def render_chat_embed(
    answer: str,
    model: str = "",
    author: str = "",
    footer: str = "",
) -> discord.Embed:
    """Render an answer as a Discord embed.

    Code blocks are moved out of the prose and listed below it, so the
    embed stays readable and the code keeps its own formatting.
    """
    prose, blocks = split_code_blocks(answer)

    embed = discord.Embed(colour=_embed_colour())
    if author:
        embed.set_author(name=author)
    embed.description = (prose or "*…*")[:EMBED_DESCRIPTION_LIMIT]

    for index, (language, code) in enumerate(blocks[:3], start=1):
        tag = LANGUAGE_ALIASES.get(language, language or "text")
        title = f"Code {index}" if len(blocks) > 1 else "Code"
        embed.add_field(
            name=title,
            value=f"```{tag}\n{code[:900]}\n```",
            inline=False,
        )

    if footer:
        embed.set_footer(text=footer)
    elif model:
        embed.set_footer(text=model)
    return embed


def render_chat(answer: str) -> str:
    """!chat / — the LLM answer, rendered as a quote block.

    Kept for the simple, short-answer case; longer answers use
    :func:`render_chat_embed`.
    """
    return f"> 🤖 {answer}"


def render_chat_stream(answer: str, model: str = "") -> str:
    """The answer as it is streamed into the channel.

    While the model is still writing, the message shows a live indicator;
    once the answer is complete it shows the answer itself.
    """
    if not answer:
        return f"🤖 *{model} est en train d'écrire…*" if model else "🤖 *…*"
    return f"> 🤖 {answer}"


def render_chat_error(kind: str, detail: str = "") -> str:
    """The message shown when the model could not answer.

    ``kind`` is one of ``unavailable``, ``model_missing``, ``timeout`` or
    ``empty`` — each failure gets its own actionable message.
    """
    messages = {
        "unavailable": (
            "😞 **Ollama ne répond pas.** Vérifie que le serveur est démarré "
            "(`ollama serve`)."
        ),
        "model_missing": (
            "🧠 **Modèle introuvable.** Installe-le avec "
            "`ollama pull <modèle>` ou change `OLLAMA_MODEL` dans le `.env`."
        ),
        "timeout": (
            "⏳ **Trop long.** Le modèle n'a pas fini à temps — essaie plus "
            "court ou un modèle plus rapide."
        ),
        "empty": (
            "🤷 **Réponse vide.** Le modèle a épuisé son budget de tokens en "
            "réfléchissant. Essaie encore ou baisse `OLLAMA_THINK`."
        ),
        "generic": "😞 **Ollama n'a pas répondu.** Réessaie dans un instant.",
    }
    message = messages.get(kind, messages["generic"])
    if detail:
        message = f"{message}\n> {detail[:300]}"
    return message


def render_chat_thinking() -> str:
    """The acknowledgement shown while the model starts working."""
    return "🤖 *Je réfléchis…*"


__all__ = [
    "CODE_BLOCK_RE",
    "DISCORD_CHAR_LIMIT",
    "EMBED_DESCRIPTION_LIMIT",
    "render_chat",
    "render_chat_embed",
    "render_chat_error",
    "render_chat_stream",
    "render_chat_thinking",
    "split_code_blocks",
]

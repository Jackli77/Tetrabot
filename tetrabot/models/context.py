"""Picking the right context to send to the model.

Feeding the model every recent message makes it answer the wrong thing: it
sees the bot's own replies, repeated messages, and unrelated chatter.  This
module decides what is actually worth sending.

The rules are simple and deliberately conservative:

* skip the bot's own messages (they are already in the memory),
* skip empty messages and messages that are only an emoji,
* skip command invocations — they are noise for a conversation,
* skip consecutive duplicates,
* keep the most recent messages that fit in the budget.
"""
from __future__ import annotations

import re

#: A message that only contains a mention of the bot.
BOT_MENTION_RE = re.compile(r"^<@!?\d+>\s*$")

#: A command invocation at the start of a message.
COMMAND_RE = re.compile(r"^[!/]\w+")


def is_noise(content: str, bot_id: int | None = None) -> bool:
    """Whether a message is worthless as context.

    ``bot_id`` lets the caller drop the bot's own messages; without it the
    function only judges the text itself.
    """
    text = (content or "").strip()
    if not text:
        return True
    if bot_id is not None and f"<@{bot_id}>" in text:
        # A message addressed to the bot is handled by the command itself.
        return True
    if BOT_MENTION_RE.match(text):
        return True
    if COMMAND_RE.match(text):
        return True
    # A message made of nothing but emoji carries no context.
    return not any(char.isalnum() for char in text)


def select_context(
    messages: list[tuple[str, str]],
    limit: int,
    bot_id: int | None = None,
) -> list[str]:
    """Pick the context lines worth sending to the model.

    ``messages`` is a list of ``(author, content)`` pairs, oldest first.
    The result is at most ``limit`` lines, in the same order, with the noisy
    ones removed.
    """
    if limit <= 0:
        return []

    selected: list[str] = []
    previous: str | None = None
    for author, content in messages:
        if is_noise(content, bot_id):
            continue
        text = content.strip()
        if text == previous:
            continue  # the same message twice in a row
        previous = text
        selected.append(f"{author}: {text}")

    # Keep the most recent ones, but restore the chronological order.
    return selected[-limit:]


__all__ = ["is_noise", "select_context"]

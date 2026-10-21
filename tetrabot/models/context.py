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
from dataclasses import dataclass

#: A message that only contains a mention of the bot.
BOT_MENTION_RE = re.compile(r"^<@!?\d+>\s*$")

#: A command invocation at the start of a message.
COMMAND_RE = re.compile(r"^[!/]\w+")


@dataclass(frozen=True)
class ChannelMessage:
    """One message of the channel, as the model needs it.

    The author's id travels with their name: it is the only reliable way to
    recognise the bot's own messages, and a bot that reads its own answers
    ends up answering them.
    """

    author: str
    author_id: int
    content: str


def as_channel_message(item: ChannelMessage | tuple[str, str]) -> ChannelMessage:
    """Normalise a message into a :class:`ChannelMessage`.

    Plain ``(author, content)`` pairs are accepted as well, so a caller that
    does not know the author ids can still use the selection.
    """
    if isinstance(item, ChannelMessage):
        return item
    author, content = item
    return ChannelMessage(author=author, author_id=0, content=content)


def is_bot_message(message: ChannelMessage, bot_id: int | None = None) -> bool:
    """Whether the message was written by the bot itself."""
    return bot_id is not None and message.author_id == bot_id


def is_noise(
    content: str,
    bot_id: int | None = None,
    drop_addressed: bool = True,
) -> bool:
    """Whether a message is worthless as context.

    ``bot_id`` lets the caller drop the messages that are addressed to the
    bot; without it the function only judges the text itself.
    ``drop_addressed`` is turned off in the channel the bot listens to:
    there, addressing the bot is a perfectly normal thing to do.
    """
    text = (content or "").strip()
    if not text:
        return True
    if drop_addressed and bot_id is not None and f"<@{bot_id}>" in text:
        # A message addressed to the bot is handled by the command itself.
        return True
    if drop_addressed and BOT_MENTION_RE.match(text):
        return True
    if COMMAND_RE.match(text):
        return True
    # A message made of nothing but emoji carries no context.
    return not any(char.isalnum() for char in text)


def select_context(
    messages: list[ChannelMessage | tuple[str, str]],
    limit: int,
    bot_id: int | None = None,
    drop_addressed: bool = True,
) -> list[str]:
    """Pick the context lines worth sending to the model.

    ``messages`` is a list of :class:`ChannelMessage` (or of plain
    ``(author, content)`` pairs), oldest first.
    The result is at most ``limit`` lines, in the same order, with the noisy
    ones removed.
    """
    if limit <= 0:
        return []

    selected: list[str] = []
    previous: str | None = None
    for item in messages:
        message = as_channel_message(item)
        if is_bot_message(message, bot_id):
            continue
        if is_noise(message.content, bot_id, drop_addressed):
            continue
        text = message.content.strip()
        if text == previous:
            continue  # the same message twice in a row
        previous = text
        selected.append(f"{message.author}: {text}")

    # Keep the most recent ones, but restore the chronological order.
    return selected[-limit:]


__all__ = [
    "BOT_MENTION_RE",
    "COMMAND_RE",
    "ChannelMessage",
    "as_channel_message",
    "is_bot_message",
    "is_noise",
    "select_context",
]

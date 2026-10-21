"""Conversation memory — the bot remembers what was said.

A chatbot that forgets everything between two questions feels broken.  This
module keeps a short, per-channel transcript of the exchanges so the model
can answer "and what about him?" with the right pronouns.

The memory is deliberately simple and in-memory:

* a **transcript** of the last exchanges in a channel,
* a **TTL**, so a channel that goes quiet forgets its history,
* a cap on the number of remembered messages, so memory never grows without
  bound.

Because it lives in the Model layer it knows nothing about Discord: it
stores plain strings.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field


@dataclass
class Turn:
    """One exchange: what the user said, and what the bot answered."""

    user: str
    assistant: str = ""
    author: str = ""

    def as_context(self) -> list[str]:
        """The turn rendered as context lines for the model.

        The user line carries the author name so the model can tell who
        said what; the answer line is marked so the model does not mistake
        its own previous replies for user input.
        """
        lines = []
        if self.author:
            lines.append(f"{self.author}: {self.user}")
        else:
            lines.append(self.user)
        if self.assistant:
            lines.append(f"[bot]: {self.assistant}")
        return lines


@dataclass
class Conversation:
    """The remembered exchanges of one channel."""

    turns: list[Turn] = field(default_factory=list)
    updated_at: float = field(default_factory=time.monotonic)

    def add(self, turn: Turn) -> None:
        """Remember an exchange."""
        self.turns.append(turn)
        self.updated_at = time.monotonic()

    def context(self, max_lines: int) -> list[str]:
        """The most recent exchanges as context lines for the model.

        ``max_lines`` bounds the number of *lines* returned, not the number
        of turns, so the caller can reason in terms of the context window.
        """
        if max_lines <= 0:
            return []
        lines: list[str] = []
        for turn in reversed(self.turns):
            turn_lines = turn.as_context()
            if len(lines) + len(turn_lines) > max_lines and lines:
                break
            lines = turn_lines + lines
        return lines

    def clear(self) -> None:
        """Forget everything."""
        self.turns.clear()
        self.updated_at = time.monotonic()


class ConversationStore:
    """A TTL'd store of :class:`Conversation` objects, keyed by channel.

    Conversations are evicted when they have not been touched for ``ttl``
    seconds, and the store itself is capped so a busy server cannot grow it
    without bound.
    """

    def __init__(self, max_messages: int = 20, ttl: float = 3600.0, max_channels: int = 200):
        self.max_messages = max_messages
        self.ttl = ttl
        self.max_channels = max_channels
        self._conversations: OrderedDict[int, Conversation] = OrderedDict()

    def get(self, channel_id: int) -> Conversation:
        """The conversation of a channel, created on first use."""
        self._evict_expired()
        conversation = self._conversations.get(channel_id)
        if conversation is None:
            conversation = Conversation()
            self._conversations[channel_id] = conversation
            self._evict_oldest()
        else:
            # Mark it as the most recently used one.
            self._conversations.move_to_end(channel_id)
        return conversation

    def add(self, channel_id: int, user: str, assistant: str = "", author: str = "") -> Turn:
        """Remember an exchange in a channel."""
        turn = Turn(user=user, assistant=assistant, author=author)
        self.get(channel_id).add(turn)
        return turn

    def context(self, channel_id: int, max_lines: int | None = None) -> list[str]:
        """The remembered context of a channel.

        ``max_lines`` bounds the number of context lines returned; it
        defaults to the store's ``max_messages``.
        """
        if max_lines is None:
            max_lines = self.max_messages
        return self.get(channel_id).context(max_lines)

    def clear(self, channel_id: int) -> None:
        """Forget a channel's conversation."""
        conversation = self._conversations.get(channel_id)
        if conversation is not None:
            conversation.clear()

    def forget(self, channel_id: int) -> None:
        """Drop a channel's conversation entirely."""
        self._conversations.pop(channel_id, None)

    def _evict_expired(self) -> None:
        """Drop the conversations that have not been used for ``ttl`` seconds."""
        if self.ttl <= 0:
            return
        now = time.monotonic()
        expired = [
            key
            for key, conversation in self._conversations.items()
            if now - conversation.updated_at > self.ttl
        ]
        for key in expired:
            del self._conversations[key]

    def _evict_oldest(self) -> None:
        """Keep the store within its channel budget."""
        while len(self._conversations) > self.max_channels:
            self._conversations.popitem(last=False)


__all__ = ["Conversation", "ConversationStore", "Turn"]

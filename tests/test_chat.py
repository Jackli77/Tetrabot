"""Tests for the chatbot — memory, context selection, rendering and errors.

The chatbot is the part of the bot a user talks to the most, so these tests
lock down the behaviour that makes it feel good: it remembers, it streams,
it picks the right context, and it explains its failures.
"""
from __future__ import annotations

import pytest

from tetrabot.controllers.commands import chat as chat_cmd
from tetrabot.models import context as ctx_model
from tetrabot.models import llm
from tetrabot.models.memory import ConversationStore
from tetrabot.views import chat as chat_view


class TestMemory:
    """The conversation memory gives the bot a real recall."""

    def test_remembers_the_exchange(self):
        store = ConversationStore()
        store.add(1, "salut", "bonjour", "alice")
        assert store.context(1, 10) == ["alice: salut", "[bot]: bonjour"]

    def test_several_exchanges_are_kept_in_order(self):
        store = ConversationStore()
        store.add(1, "un", "1", "alice")
        store.add(1, "deux", "2", "alice")
        assert store.context(1, 10) == [
            "alice: un", "[bot]: 1", "alice: deux", "[bot]: 2",
        ]

    def test_only_the_last_exchanges_are_kept(self):
        store = ConversationStore()
        for i in range(5):
            store.add(1, f"msg{i}", f"rep{i}", "alice")
        # The budget is counted in context lines, not in turns.
        assert store.context(1, 2) == ["alice: msg4", "[bot]: rep4"]

    def test_conversations_are_separate_per_channel(self):
        store = ConversationStore()
        store.add(1, "salut", "bonjour", "alice")
        store.add(2, "autre", "canal", "bob")
        assert store.context(1, 10) == ["alice: salut", "[bot]: bonjour"]
        assert store.context(2, 10) == ["bob: autre", "[bot]: canal"]

    def test_forget_drops_the_conversation(self):
        store = ConversationStore()
        store.add(1, "salut", "bonjour", "alice")
        store.forget(1)
        assert store.context(1, 10) == []

    def test_expired_conversations_are_evicted(self):
        import time

        store = ConversationStore(ttl=0.0001)
        store.add(1, "salut", "bonjour", "alice")
        time.sleep(0.01)
        assert store.context(1, 10) == []

    def test_the_store_stays_within_its_channel_budget(self):
        store = ConversationStore(max_channels=3)
        for channel in range(10):
            store.add(channel, "x", "y", "a")
        assert len(store._conversations) <= 3


class TestContextSelection:
    """The model must not be fed the noise of the channel."""

    def test_empty_messages_are_dropped(self):
        assert ctx_model.is_noise("") is True
        assert ctx_model.is_noise("   ") is True

    def test_commands_are_dropped(self):
        assert ctx_model.is_noise("!inc") is True
        assert ctx_model.is_noise("/chat bonjour") is True

    def test_emoji_only_messages_are_dropped(self):
        assert ctx_model.is_noise("😀") is True

    def test_real_messages_are_kept(self):
        assert ctx_model.is_noise("salut") is False

    def test_messages_addressed_to_the_bot_are_dropped(self):
        assert ctx_model.is_noise("<@123> salut", bot_id=123) is True
        assert ctx_model.is_noise("salut", bot_id=123) is False

    def test_select_keeps_the_useful_messages(self):
        messages = [
            ("alice", "salut"),
            ("bot", "<@1> salut"),
            ("bob", "!gamble 10"),
            ("carol", "   "),
            ("dave", "😀"),
            ("eve", "comment ça va ?"),
        ]
        selected = ctx_model.select_context(messages, limit=10, bot_id=1)
        assert selected == ["alice: salut", "eve: comment ça va ?"]

    def test_select_respects_the_limit_and_keeps_the_newest(self):
        messages = [(f"u{i}", f"message {i}") for i in range(10)]
        selected = ctx_model.select_context(messages, limit=3)
        assert selected == ["u7: message 7", "u8: message 8", "u9: message 9"]

    def test_consecutive_duplicates_are_dropped(self):
        messages = [("a", "pareil"), ("b", "pareil"), ("c", "autre")]
        selected = ctx_model.select_context(messages, limit=10)
        assert selected == ["a: pareil", "c: autre"]


class TestChatRendering:
    """How the answer is presented."""

    def test_short_answer_is_a_quote(self):
        assert chat_view.render_chat("bonjour") == "> 🤖 bonjour"

    def test_code_blocks_are_split_out(self):
        prose, blocks = chat_view.split_code_blocks(
            "Voici:\n```python\nprint(1)\n```\nfin"
        )
        assert blocks == [("python", "print(1)")]
        assert "print(1)" not in prose
        assert "Voici" in prose

    def test_embed_carries_the_prose_and_the_code(self):
        embed = chat_view.render_chat_embed(
            "Voici:\n```py\nx = 1\n```", model="qwen3:4b"
        )
        assert "Voici" in embed.description
        assert len(embed.fields) == 1
        assert "x = 1" in embed.fields[0].value
        assert embed.footer.text == "qwen3:4b"

    def test_embed_of_an_empty_answer_is_still_valid(self):
        embed = chat_view.render_chat_embed("")
        assert embed.description is not None

    def test_stream_placeholder_before_the_first_word(self):
        assert "en train" in chat_view.render_chat_stream("", "qwen3:4b")

    def test_stream_shows_the_answer_once_it_arrives(self):
        assert chat_view.render_chat_stream("bonjour") == "> 🤖 bonjour"

    @pytest.mark.parametrize(
        "kind", ["unavailable", "model_missing", "timeout", "empty", "generic"]
    )
    def test_every_failure_has_its_own_message(self, kind):
        message = chat_view.render_chat_error(kind)
        assert message
        assert message != chat_view.render_chat_error("generic") or kind == "generic"

    def test_the_failure_message_can_carry_a_detail(self):
        message = chat_view.render_chat_error("timeout", "took 180s")
        assert "took 180s" in message


class TestErrorClassification:
    """Each failure must be told apart from the others."""

    def test_model_missing(self):
        assert chat_cmd._error_kind(llm.OllamaModelMissing("x")) == "model_missing"

    def test_timeout(self):
        assert chat_cmd._error_kind(llm.OllamaTimeout("x")) == "timeout"

    def test_unavailable(self):
        assert chat_cmd._error_kind(llm.OllamaUnavailable("x")) == "unavailable"

    def test_empty(self):
        assert chat_cmd._error_kind(llm.OllamaEmpty("x")) == "empty"

    def test_anything_else_is_generic(self):
        assert chat_cmd._error_kind(RuntimeError("boom")) == "generic"

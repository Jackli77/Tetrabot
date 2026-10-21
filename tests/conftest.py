"""Shared pytest fixtures and fakes.

The fakes mimic just enough of the Discord API for the command logic to run
without a network connection.
"""
from __future__ import annotations

import pytest

from tetrabot.controllers.context import CommandContext


class FakeAvatar:
    """A stand-in for a Discord avatar."""

    def __init__(self, user_id: int = 1):
        self.url = f"https://cdn.discordapp.com/avatars/{user_id}.png"


class FakeUser:
    """A stand-in for a Discord user."""

    def __init__(self, user_id: int = 1, name: str = "alice"):
        self.id = user_id
        self.name = name
        self.display_name = name
        self.mention = f"<@{user_id}>"
        self.bot = False
        self.display_avatar = FakeAvatar(user_id)


class FakeClient:
    """A stand-in for the Discord client."""

    def __init__(self, name: str = "alice"):
        self.user = FakeUser(0, "BOT")
        self._name = name

    async def fetch_user(self, user_id: int) -> FakeUser:
        return FakeUser(user_id, self._name)


class FakeChannel:
    """A stand-in for a Discord channel that records what was sent."""

    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)
        return FakeMessage()


class FakeMessage:
    """A stand-in for a sent Discord message."""

    def __init__(self):
        self.deleted = False

    async def delete(self):
        self.deleted = True


class RecordingResponder:
    """A responder that records every payload instead of sending it."""

    def __init__(self):
        self.sent: list[dict] = []
        self.edits: list[dict] = []

    async def __call__(self, content=None, embed=None, view=None, ephemeral=False):
        self.sent.append(
            {"content": content, "embed": embed, "view": view, "ephemeral": ephemeral}
        )
        return None

    async def defer(self):
        return None

    async def edit(self, content=None, embed=None):
        """Record the streamed edits of the answer."""
        self.edits.append({"content": content, "embed": embed})
        return None

    @property
    def edited_contents(self) -> list[str]:
        """The texts the responder was edited with."""
        return [edit["content"] for edit in self.edits]


class FakeUsers:
    """A minimal async stand-in for the MongoDB ``users`` collection."""

    def __init__(self):
        self.docs: dict[int, dict] = {}

    async def update_one(self, flt, update, upsert=False, **kwargs):
        doc = self.docs.get(flt["_id"])
        if doc is None and upsert:
            doc = {"_id": flt["_id"]}
            doc.update(update.get("$setOnInsert", {}))
            self.docs[flt["_id"]] = doc

    async def find_one(self, flt, **kwargs):
        doc = self.docs.get(flt["_id"])
        return dict(doc) if doc else None

    async def find_one_and_update(self, flt, update, return_document=False, **kwargs):
        doc = self.docs[flt["_id"]]
        for field, amount in update.get("$inc", {}).items():
            doc[field] = doc.get(field, 0) + amount
        return dict(doc)

    def find(self, *args, **kwargs):
        """A minimal cursor over the in-memory documents."""
        docs = list(self.docs.values())
        return FakeCursor(docs)


class FakeCursor:
    """A minimal async cursor over a list of documents."""

    def __init__(self, docs):
        self._docs = docs

    def sort(self, field, direction=-1):
        self._docs = sorted(
            self._docs, key=lambda d: d.get(field, 0), reverse=direction < 0
        )
        return self

    async def to_list(self, length=None):
        return self._docs if length is None else self._docs[:length]

    def __aiter__(self):
        async def gen():
            for doc in self._docs:
                yield doc

        return gen()


@pytest.fixture
def fake_users() -> FakeUsers:
    """An in-memory stand-in for the ``users`` collection."""
    return FakeUsers()


@pytest.fixture
def make_ctx():
    """Build a :class:`CommandContext` whose responder records every payload."""

    def _make(author=None, client=None, args=None, prefix="!", ephemeral=False):
        responder = RecordingResponder()
        ctx = CommandContext(
            author=author or FakeUser(1, "alice"),
            channel=FakeChannel(),
            client=client if client is not None else FakeClient(),
            args=list(args or []),
            respond=responder,
            prefix=prefix,
            ephemeral=ephemeral,
        )
        return ctx, responder

    return _make


@pytest.fixture
def score_lines():
    """Extract the post-duel score lines from a responder's payloads."""

    def _extract(responder) -> list[str]:
        return [
            payload["content"]
            for payload in responder.sent
            if payload.get("content") and "équité" in payload["content"]
        ]

    return _extract

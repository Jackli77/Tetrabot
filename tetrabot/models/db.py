"""Database infrastructure: the async MongoDB connection and collections."""
from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient

from tetrabot import config

logger = logging.getLogger(__name__)

#: The Motor client, created lazily so importing this module never opens a
#: connection (tests import it without any database at hand).
_client: AsyncIOMotorClient | None = None


def client() -> AsyncIOMotorClient:
    """The shared Motor client, created on first use."""
    global _client
    if _client is None:
        if not config.MONGODB_URI:
            raise RuntimeError(
                "MONGODB_URI is not set — copy .env.example to .env and fill it in."
            )
        _client = AsyncIOMotorClient(config.MONGODB_URI)
    return _client


def database():
    """The ``tetrabot`` database."""
    return client()["tetrabot"]


def users():
    """The ``users`` collection — one document per Discord user."""
    return database()["users"]


async def initialize(discord_client) -> None:
    """Sync stored usernames against Discord at startup."""
    collection = users()
    cursor = collection.find({}, {"_id": 1})
    async for doc in cursor:
        try:
            user = await discord_client.fetch_user(doc["_id"])
            await collection.update_one({"_id": doc["_id"]}, {"$set": {"username": user.name}})
        except Exception as exc:  # noqa: BLE001 - one bad user must not stop the bot
            logger.warning("Could not fetch user %s: %s", doc["_id"], exc)
    logger.info("Database initialised.")


__all__ = ["client", "database", "initialize", "users"]

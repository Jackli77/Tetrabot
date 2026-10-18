"""MODEL infrastructure: async MongoDB connection and collections."""
from config import settings
from motor.motor_asyncio import AsyncIOMotorClient

# Create the async Motor client from the URI in .env
_client = AsyncIOMotorClient(settings.MONGODB_URI)

# Database and collection references — import these elsewhere
db = _client["tetrabot"]
users = db["users"]


async def initialize(client):
    """Sync stored usernames against Discord at startup."""
    cursor = users.find({}, {"_id": 1})
    async for doc in cursor:
        try:
            user = await client.fetch_user(doc["_id"])
            await users.update_one(
                {"_id": doc["_id"]},
                {"$set": {"username": user.name}}
            )
        except Exception as e:
            print(f"Could not fetch user {doc['_id']}: {e}")
    print("Database initialised.", flush=True)

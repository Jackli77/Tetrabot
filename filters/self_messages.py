"""FILTERS layer: drop the bot's own messages (anti-loop guard)."""
from filters.base import FilterResult, MessageFilter


class IgnoreSelfFilter(MessageFilter):
    """Stop the pipeline when the message was sent by the bot itself."""

    async def apply(self, message, bot_client, result: FilterResult) -> FilterResult:
        if message.author == bot_client.user:
            result.proceed = False
        return result

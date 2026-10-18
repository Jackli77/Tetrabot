"""FILTERS layer: route direct messages to the DM controller.

Sets ``result.extra["dm"]`` and picks the matching controller entry
point (``controllers.dm.router`` vs ``controllers.prefix.router``).
"""
from controllers.dm.router import handle_command as handle_dm_command
from controllers.prefix.router import handle_command as handle_guild_command
from filters.base import FilterResult, MessageFilter


class DirectMessageFilter(MessageFilter):
    """Flag DMs and select the DM or guild command handler accordingly."""

    async def apply(self, message, bot_client, result: FilterResult) -> FilterResult:
        if message.channel == message.author.dm_channel:
            result.extra["dm"] = True
            result.handler = handle_dm_command
        else:
            result.extra["dm"] = False
            result.handler = handle_guild_command
        return result

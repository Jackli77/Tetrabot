"""FILTERS layer: parse the ``!command args`` prefix (or stop when absent)."""
from filters.base import FilterResult, MessageFilter


class PrefixFilter(MessageFilter):
    """Parse the command prefix; stop silently when the message has none.

    Stopping silently (instead of replying) avoids spamming channels the
    bot shares with other bots that use the same prefix.
    """

    def __init__(self, prefix: str | None = None):
        from config import settings as _settings

        self.prefix = prefix if prefix is not None else _settings.COMMAND_PREFIX

    async def apply(self, message, bot_client, result: FilterResult) -> FilterResult:
        text = message.content or ""
        if not text.startswith(self.prefix) or text == self.prefix:
            result.proceed = False
            return result
        parts = text[len(self.prefix):].split()
        result.command = parts[0].lower()
        result.args = parts[1:]
        return result

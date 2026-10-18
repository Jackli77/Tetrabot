"""FILTERS layer: chain several filters into one message pipeline."""
from filters.base import FilterResult, MessageFilter
from filters.direct_messages import DirectMessageFilter
from filters.prefix import PrefixFilter
from filters.self_messages import IgnoreSelfFilter


class FilterPipeline:
    """Run filters in order; stop at the first one that sets ``proceed=False``."""

    def __init__(self, *filters: MessageFilter):
        self.filters = list(filters)

    async def run(self, message, bot_client) -> FilterResult:
        """Thread a fresh :class:`FilterResult` through every filter."""
        result = FilterResult()
        for message_filter in self.filters:
            result = await message_filter.apply(message, bot_client, result)
            if not result.proceed:
                break
        return result


def default_pipeline(prefix: str | None = None) -> FilterPipeline:
    """The standard pipeline used by the bot: self-guard, routing, prefix."""
    return FilterPipeline(
        IgnoreSelfFilter(),
        DirectMessageFilter(),
        PrefixFilter(prefix=prefix),
    )

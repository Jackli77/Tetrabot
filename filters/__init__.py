"""FILTERS layer: small composable gates for incoming Discord messages.

Each filter inspects a message and either lets it through or stops the
pipeline (:attr:`FilterResult.proceed`).  Filters never send messages and
never touch the database — they only classify and route:

* ``IgnoreSelfFilter`` — drop the bot's own messages.
* ``DirectMessageFilter`` — pick the DM or guild command handler.
* ``PrefixFilter`` — parse ``!command args`` (or stop when there is none).

Chain them with :class:`FilterPipeline` (see ``filters/pipeline.py``) or
use :func:`default_pipeline` for the standard order.
"""
from filters.base import FilterResult, MessageFilter
from filters.direct_messages import DirectMessageFilter
from filters.pipeline import FilterPipeline, default_pipeline
from filters.prefix import PrefixFilter
from filters.self_messages import IgnoreSelfFilter

__all__ = [
    "DirectMessageFilter",
    "FilterResult",
    "FilterPipeline",
    "IgnoreSelfFilter",
    "MessageFilter",
    "PrefixFilter",
    "default_pipeline",
]

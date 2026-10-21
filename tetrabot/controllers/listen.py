"""CONTROLLER/``: the listening transport.

The bot does not only answer when it is asked with a command: in the
channel it listens to, it answers *every* message.  This controller is
that third transport, next to the ``!`` prefix and the ``/`` slash tree.

:class:`ListenController` recognises the messages of the listening channel
and builds the same :class:`tetrabot.controllers.context.CommandContext` the
other transports build, so the chatbot behaviour is shared — and written
only once.

Two things make the mode bearable:

* **one answer at a time.**  A local model is a scarce resource, and two
  answers racing each other would interleave in the channel.  The messages
  of a channel are therefore queued and answered in order.
* **no answer to itself.**  The bot ignores its own messages, so it never
  answers its own answer.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from tetrabot import catalog, config
from tetrabot.controllers.base import BaseController, DetectionResult
from tetrabot.controllers.context import CommandContext
from tetrabot.models.context import COMMAND_RE
from tetrabot.views.responders import PrefixResponder

logger = logging.getLogger(__name__)

#: The name of the transport, as the other controllers name theirs.
TRANSPORT_NAME = "listen"


class ChannelQueue:
    """One queue of messages per channel.

    The messages of a channel are answered one after the other, in the
    order they were sent.  Different channels do not wait for each other:
    a slow answer in one channel must not silence another one.
    """

    def __init__(self) -> None:
        self._queues: dict[int, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._workers: dict[int, asyncio.Task] = {}

    def submit(self, channel_id: int, job) -> None:
        """Queue a job for a channel and make sure its worker is running."""
        self._queues[channel_id].put_nowait(job)
        worker = self._workers.get(channel_id)
        if worker is None or worker.done():
            self._workers[channel_id] = asyncio.create_task(
                self._drain(channel_id), name=f"tetrabot-listen-{channel_id}"
            )

    async def _drain(self, channel_id: int) -> None:
        """Answer the queued messages of a channel, one after the other."""
        queue = self._queues[channel_id]
        while True:
            job = await queue.get()
            try:
                await job()
            except Exception:
                # A failed answer must never kill the worker: the next
                # message of the channel still has to be answered.
                logger.exception("Could not answer a message of the channel")
            finally:
                queue.task_done()


class ListenController(BaseController):
    """Detect the messages of the channel the bot listens to."""

    name = TRANSPORT_NAME

    def __init__(self, channel_name: str | None = None):
        self.channel_name = (
            channel_name if channel_name is not None else config.CHAT_CHANNEL
        )
        #: The queue of the messages waiting to be answered, per channel.
        self.queue = ChannelQueue()

    # -- detection --------------------------------------------------------

    def _is_listening_channel(
        self, message, bot_client, result: DetectionResult
    ) -> bool:
        """Whether the message was sent in the channel the bot listens to.

        A message of another channel is not ours: it must be left alone.
        """
        name = getattr(message.channel, "name", "") or ""
        if name.lower() != self.channel_name.lower():
            result.handled = False
            return False
        return True

    def _ignore_self(self, message, bot_client, result: DetectionResult) -> bool:
        """Return False (stop) when the message was sent by the bot itself."""
        if message.author == bot_client.user:
            result.handled = False
            return False
        return True

    def _ignore_empty(self, message, bot_client, result: DetectionResult) -> bool:
        """Return False (stop) when the message has nothing to answer."""
        content = (message.content or "").strip()
        if not content:
            result.handled = False
            return False
        result.args = [content]
        return True

    def _ignore_command(self, message, bot_client, result: DetectionResult) -> bool:
        """Return False (stop) when the message is a command.

        A command is already handled by the ``!`` controller: answering it
        with the chatbot too would run the command *and* explain it.
        """
        if COMMAND_RE.match(result.args[0] if result.args else ""):
            result.handled = False
            return False
        return True

    async def detect(self, message, bot_client) -> DetectionResult:
        """Run every step in order; stop at the first miss."""
        result = DetectionResult()
        steps = (
            self._ignore_self,
            self._is_listening_channel,
            self._ignore_empty,
            self._ignore_command,
        )
        for step in steps:
            if not step(message, bot_client, result):
                break
        return result

    # -- transport specific steps ----------------------------------------

    def build_context(
        self, spec, result: DetectionResult, message, bot_client
    ) -> CommandContext:
        """Build the shared context for a message of the listening channel."""
        return CommandContext(
            author=message.author,
            channel=message.channel,
            client=bot_client,
            args=list(result.args),
            respond=PrefixResponder(message),
            prefix=TRANSPORT_NAME,
        )


async def handle_message(
    message,
    bot_client,
    controller: ListenController | None = None,
) -> DetectionResult:
    """Answer a message of the listening channel, if it is one.

    The message is queued instead of being answered right away: the
    messages of a channel are answered in the order they were sent, and a
    local model is never asked two questions at the same time.
    """
    controller = controller or ListenController()
    result = await controller.detect(message, bot_client)

    if not result.handled or not result.args:
        return result

    spec = catalog.find("chat")
    if spec is None:
        logger.error("The chat command is missing from the catalog")
        return result

    logger.info("listening: %s: %s", message.author.name, result.args[0])

    async def job() -> None:
        await controller.dispatch(spec, result, message, bot_client)

    controller.queue.submit(getattr(message.channel, "id", 0) or 0, job)
    return result


__all__ = ["TRANSPORT_NAME", "ChannelQueue", "ListenController", "handle_message"]

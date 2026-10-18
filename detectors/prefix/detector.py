"""DETECTOR/``!``: recognise prefix invocations in Discord messages.

:class:`PrefixDetector` runs the three detection steps in order and stops at
the first miss (all misses are silent, to avoid spamming channels shared
with other bots):

1. ``_ignore_self`` — drop the bot's own messages (anti-loop guard).
2. ``_route`` — flag DMs (``extra["dm"]``) and pick the matching ``!``
   handler (``detectors.prefix.dm.router`` vs ``detectors.prefix.router``).
3. ``_parse_prefix`` — parse ``!command args`` (lowercased command name).

:func:`handle_message` runs detection and dispatches to the chosen handler,
which builds a shared :class:`controllers.CommandContext` and calls the
same ``controllers.LOGIC`` functions the ``/`` detector uses.
"""
from config import settings
from detectors.base import BaseDetector, DetectionResult
from detectors.prefix.dm.router import handle_command as handle_dm_command
from detectors.prefix.router import handle_command as handle_guild_command


class PrefixDetector(BaseDetector):
    """Detect ``!command args`` invocations in Discord messages."""

    name = "!"

    def __init__(self, prefix: str | None = None):
        self.prefix = prefix if prefix is not None else settings.COMMAND_PREFIX

    def _ignore_self(self, message, bot_client, result: DetectionResult) -> bool:
        """Return False (stop) when the message was sent by the bot itself."""
        if message.author == bot_client.user:
            result.handled = False
            return False
        return True

    def _route(self, message, bot_client, result: DetectionResult) -> bool:
        """Flag DMs and select the DM or guild ``!`` handler."""
        if message.channel == message.author.dm_channel:
            result.extra["dm"] = True
            result.handler = handle_dm_command
        else:
            result.extra["dm"] = False
            result.handler = handle_guild_command
        return True

    def _parse_prefix(self, message, bot_client, result: DetectionResult) -> bool:
        """Parse the command prefix; stop silently when the message has none."""
        text = message.content or ""
        if not text.startswith(self.prefix) or text == self.prefix:
            result.handled = False
            return False
        parts = text[len(self.prefix):].split()
        result.command = parts[0].lower()
        result.args = parts[1:]
        return True

    async def detect(self, message, bot_client) -> DetectionResult:
        """Run every step in order; stop at the first miss."""
        result = DetectionResult()
        for step in (self._ignore_self, self._route, self._parse_prefix):
            if not step(message, bot_client, result):
                break
        return result


async def handle_message(message, bot_client, detector: PrefixDetector | None = None):
    """Detect a ``!`` invocation in ``message`` and dispatch to its handler.

    Does nothing (silently) when the message is not a ``!`` command.
    """
    detector = detector or PrefixDetector()
    result = await detector.detect(message, bot_client)
    if not result.handled or result.command is None:
        return result
    handler = result.handler or (
        handle_dm_command if result.extra.get("dm") else handle_guild_command
    )
    try:
        await handler(result.command, result.args, message, bot_client)
    except Exception:
        print("Error while handling message", flush=True)
        raise
    return result


__all__ = ["PrefixDetector", "handle_message"]

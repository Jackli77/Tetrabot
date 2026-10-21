"""The contract every tool follows.

A tool has three parts:

* a **name** the model calls,
* a **description** that tells the model *when* to call it — this is the
  most important part, because it is all the model knows about the tool,
* a **JSON schema** of its arguments.

And one behaviour: :meth:`Tool.call` never raises.  A tool that fails
returns a result that says so, so the model can tell the user "I could not
reach the weather service" instead of the bot dying mid-answer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: The maximum size of the result handed back to the model, in characters.
#: A huge payload would eat the context window and slow everything down.
MAX_RESULT_CHARS = 2000


class ToolError(Exception):
    """A tool could not do its job.

    It is caught by the caller and turned into a result the model can read.
    """


@dataclass
class ToolResult:
    """What a tool returns.

    ``ok`` tells the model whether the lookup worked, ``data`` holds the
    answer and ``error`` explains a failure.
    """

    ok: bool = True
    data: Any = None
    error: str = ""
    source: str = ""

    def to_text(self) -> str:
        """The result as the text handed back to the model."""
        import json

        if not self.ok:
            return json.dumps({"error": self.error, "ok": False}, ensure_ascii=False)
        payload = {"ok": True, "result": self.data}
        if self.source:
            payload["source"] = self.source
        text = json.dumps(payload, ensure_ascii=False, default=str)
        if len(text) > MAX_RESULT_CHARS:
            text = text[: MAX_RESULT_CHARS - 20] + '... (truncated)"'
        return text


@dataclass
class Tool:
    """The description of one callable tool."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    handler: Any = None

    def schema(self) -> dict[str, Any]:
        """The tool in the shape Ollama expects."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}},
            },
        }

    async def call(self, **arguments: Any) -> ToolResult:
        """Call the tool, turning any failure into a result."""
        if self.handler is None:
            return ToolResult(ok=False, error=f"the tool {self.name} has no implementation")
        try:
            return await self.handler(**arguments)
        except ToolError as exc:
            return ToolResult(ok=False, error=str(exc))
        except TypeError as exc:
            # The model passed arguments the tool does not accept.
            return ToolResult(ok=False, error=f"invalid arguments for {self.name}: {exc}")
        except Exception as exc:  # noqa: BLE001 - a tool must never break the bot
            return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")


__all__ = ["MAX_RESULT_CHARS", "Tool", "ToolError", "ToolResult"]

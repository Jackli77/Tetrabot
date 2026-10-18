import settings


class BaseCommand:
    """Base class for all prefix-based bot commands.

    Each concrete command class should:
      - Call super().__init__() with a description, optional params list, and optional aliases.
      - Keep only prefix-specific transport concerns in handle() (argument
        parsing, reaction challenges, pagination UI) and delegate the actual
        command behaviour to the shared logic in the ``controllers`` package.

    The default ``handle()`` below builds a transport-agnostic
    ``CommandContext`` from the message and dispatches to the matching
    ``cmd_*`` function, so most commands don't need to override it at all.

    The command name is automatically derived from the class name in lowercase
    (e.g. a class named `Random` becomes the `!random` command).
    """

    # Key of the shared logic function inside ``controllers.LOGIC``.
    # Defaults to ``cmd_<command name>``; override when the logic function is
    # named differently (e.g. the ``Commands`` class uses ``cmd_help``).
    logic_key = None

    def __init__(self, description, params, aliases=None):
        # Derive the command name from the class name (lowercased).
        self.name = type(self).__name__.lower()
        # List of parameter names the command expects (used for help text & arg-count validation).
        self.params = params
        # Optional list of alternative names that trigger the same command.
        self.aliases = aliases or []

        # Build a human-readable description for the help/embed message.
        desc = f"**{settings.COMMAND_PREFIX}{self.name}**"

        if self.params:
            desc += " " + " ".join(f"*<{p}>*" for p in params)

        desc += f": {description}."
        self.description = desc

    def build_context(self, params, message, client):
        """Build the shared :class:`CommandContext` for this prefix command."""
        from controllers.context import CommandContext, make_prefix_respond

        return CommandContext(
            author=message.author,
            channel=message.channel,
            client=client,
            args=list(params),
            respond=make_prefix_respond(message),
            prefix=settings.COMMAND_PREFIX,
        )

    async def handle(self, params, message, client):
        """Generic transport adapter: dispatch to the shared ``cmd_*`` logic."""
        from controllers import LOGIC

        ctx = self.build_context(params, message, client)
        await LOGIC[self.logic_key or f"cmd_{self.name}"](ctx)

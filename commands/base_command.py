import settings


class BaseCommand:
    """Base class for all prefix-based bot commands.

    Each concrete command class should:
      - Call super().__init__() with a description, optional params list, and optional aliases.
      - Override the async handle() method to implement the command logic.

    The command name is automatically derived from the class name in lowercase
    (e.g. a class named `Random` becomes the `!random` command).
    """

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

    # Every command subclass must override this method with its own logic.
    async def handle(self, params, message, client):
        raise NotImplementedError  # To be defined by every command

import discord
import settings
from dms.base_dm import BaseDm


# This is a convenient command that automatically generates a helpful
# message showing all available commands
class Commands(BaseDm):

    def __init__(self):
        description = "Affiche la liste de toutes les commandes disponibles"
        params = None
        super().__init__(description, params)

    async def handle(self, params, message, client):
        from message_handler import COMMAND_HANDLERS
        from dms_handler import DMS_HANDLERS

        embed = discord.Embed(
            title="📜 Commandes disponibles",
            description=f"Préfixe de commande : `{settings.COMMAND_PREFIX}`",
            colour=discord.Colour.blue()
        )

        seen_dms = set()
        dm_lines = []
        for name, cmd in sorted(DMS_HANDLERS.items()):
            if cmd in seen_dms:
                continue
            seen_dms.add(cmd)

            param_str = " " + " ".join(f"<{p}>" for p in cmd.params) if cmd.params else ""
            cmd_signature = f"`{settings.COMMAND_PREFIX}{cmd.name}{param_str}`"

            desc = cmd.description
            if ": " in desc:
                desc = desc.split(": ", 1)[1]
            desc = desc.rstrip(".")

            dm_lines.append(f"{cmd_signature}\n↳ {desc}")

        if dm_lines:
            embed.add_field(
                name="📩 Commandes en message privé (DM)",
                value="\n\n".join(dm_lines),
                inline=False
            )

        seen_cmds = set()
        server_lines = []
        for name, cmd in sorted(COMMAND_HANDLERS.items()):
            if cmd in seen_cmds:
                continue
            seen_cmds.add(cmd)

            param_str = " " + " ".join(f"<{p}>" for p in cmd.params) if cmd.params else ""
            cmd_signature = f"`{settings.COMMAND_PREFIX}{cmd.name}{param_str}`"
            if getattr(cmd, "aliases", None):
                alias_str = ", ".join(f"`{settings.COMMAND_PREFIX}{a}`" for a in cmd.aliases)
                cmd_signature += f" *(alias: {alias_str})*"

            desc = cmd.description
            if ": " in desc:
                desc = desc.split(": ", 1)[1]
            desc = desc.rstrip(".")

            server_lines.append(f"{cmd_signature}\n↳ {desc}")

        if server_lines:
            embed.add_field(
                name="💬 Commandes de serveur",
                value="\n\n".join(server_lines),
                inline=False
            )

        await message.author.send(embed=embed)


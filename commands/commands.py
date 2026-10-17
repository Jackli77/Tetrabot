import discord
import settings
from commands.base_command import BaseCommand


# The /commands help command: lists every available server and DM command
# in a formatted Discord embed.
class Commands(BaseCommand):

    def __init__(self):
        description = "Affiche la liste de toutes les commandes disponibles"
        params = None
        super().__init__(description, params)

    async def handle(self, params, message, client):
        # Import handler registries (imported locally to avoid circular imports).
        from message_handler import COMMAND_HANDLERS
        from dms_handler import DMS_HANDLERS

        embed = discord.Embed(
            title="📜 Commandes disponibles",
            description=f"Préfixe de commande : `{settings.COMMAND_PREFIX}`",
            colour=discord.Colour.blue()
        )

        # --- Server commands -------------------------------------------------
        # Deduplicate by command instance so aliases don't create duplicate rows.
        seen_cmds = set()
        server_lines = []
        for name, cmd in sorted(COMMAND_HANDLERS.items()):
            if cmd in seen_cmds:
                continue
            seen_cmds.add(cmd)

            # Build the usage signature, e.g. `!gamble <limite>`
            param_str = " " + " ".join(f"<{p}>" for p in cmd.params) if cmd.params else ""
            cmd_signature = f"`{settings.COMMAND_PREFIX}{cmd.name}{param_str}`"
            if getattr(cmd, "aliases", None):
                alias_str = ", ".join(f"`{settings.COMMAND_PREFIX}{a}`" for a in cmd.aliases)
                cmd_signature += f" *(alias: {alias_str})*"

            # Strip the leading "`!name`:" prefix from the stored description.
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

        # --- DM commands -----------------------------------------------------
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

        await message.channel.send(embed=embed)


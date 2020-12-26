from asyncio import sleep

import discord
from commands.base_command import BaseCommand

# Your friendly example event
# Keep in0 mind that the command name will be derived from the class name
# but in lowercase:

# So, a command class named Random will generate a 'random' command
from discord.ext import commands
from discord.ext.commands import bot

from Tetrabot.events.mute_event import getMutedRole


class unmute(BaseCommand):

    def __init__(self):
        # A quick description for the help message
        description = "unmute la cible"
        # A list of parameters that the command will take as input
        # Parameters will be separated by spaces and fed to the 'params'
        # argument in the handle() method
        # If no params are expected, leave this list empty or set it to None
        params = ["cible"]
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    @commands.has_role('Admin')
    async def unmute(ctx, member: discord.Member, *, reason="no reason"):
        mutedRole = await getMutedRole(ctx)
        await member.remove_roles(mutedRole, reason=reason)
        await ctx.send(f"{member.mention} a été unmute !")



@unmute.error
async def unmute_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("T'es pas **Admin** clebard <:8219_cheems:720974989490389043>")
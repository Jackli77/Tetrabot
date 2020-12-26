import discord


async def createMutedRole(message):
    mutedRole = await message.guild.create_role(name="Muted",
                                                permissions=discord.Permissions(
                                                    send_messages=False,
                                                    speak=False),
                                                reason="Creation du role Muted pour mute des gens.")
    for channel in message.guild.channels:
        await channel.set_permissions(mutedRole, send_messages=False, speak=False)
    return mutedRole


async def getMutedRole(message):
    roles = message.guild.roles
    for role in roles:
        if role.name == "Muted":
            return role

    return await createMutedRole(message)

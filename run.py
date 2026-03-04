from pydoc import describe
import discord
import os
from discord.ext import commands, tasks
from discord.utils import get
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio
import sys
from app.bot.helper.confighelper import MEMBARR_VERSION, switch, Discord_bot_token, plex_roles, jellyfin_roles, emby_roles
import app.bot.helper.confighelper as confighelper
import app.bot.helper.jellyfinhelper as jelly
import app.bot.helper.embyhelper as emby
from app.bot.helper.message import *
from requests import ConnectTimeout
from plexapi.myplex import MyPlexAccount

maxroles = 10

if switch == 0:
    print("Missing Config.")
    sys.exit()


class Bot(commands.Bot):
    def __init__(self) -> None:
        print("Initializing Discord bot")
        intents = discord.Intents.all()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents)

    async def on_ready(self):
        print("Bot is online.")
        for guild in self.guilds:
            print("Syncing commands to " + guild.name)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    async def on_guild_join(self, guild):
        print(f"Joined guild {guild.name}")
        print(f"Syncing commands to {guild.name}")
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def setup_hook(self):
        print("Loading media server connectors")
        await self.load_extension(f'app.bot.cogs.app')


bot = Bot()


async def reload():
    await bot.reload_extension(f'app.bot.cogs.app')


async def getuser(interaction, server, type):
    value = None
    await interaction.user.send("Please reply with your {} {}:".format(server, type))
    while (value == None):
        def check(m):
            return m.author == interaction.user and not m.guild

        try:
            value = await bot.wait_for('message', timeout=200, check=check)
            return value.content
        except asyncio.TimeoutError:
            message = "Timed Out. Try again."
            return None


plex_commands = app_commands.Group(name="plexsettings", description="Membarr Plex commands")
jellyfin_commands = app_commands.Group(name="jellyfinsettings", description="Membarr Jellyfin commands")
emby_commands = app_commands.Group(name="embysettings", description="Membarr Emby commands")


@plex_commands.command(name="addrole", description="Add a role to automatically add users to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexroleadd(interaction: discord.Interaction, role: discord.Role):
    if len(plex_roles) <= maxroles:
        # Do not add roles multiple times.
        if role.name in plex_roles:
            await embederror(interaction.response, f"Plex role \"{role.name}\" already added.")
            return

        plex_roles.append(role.name)
        saveroles = ",".join(plex_roles)
        confighelper.change_config("plex_roles", saveroles)
        await interaction.response.send_message("Updated Plex roles. Bot is restarting. Please wait.", ephemeral=True)
        print("Plex roles updated. Restarting bot, Give it a few seconds.")
        await reload()
        print("Bot has been restarted. Give it a few seconds.")


@plex_commands.command(name="removerole", description="Stop adding users with a role to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexroleremove(interaction: discord.Interaction, role: discord.Role):
    if role.name not in plex_roles:
        await embederror(interaction.response, f"\"{role.name}\" is currently not a Plex role.")
        return
    plex_roles.remove(role.name)
    confighelper.change_config("plex_roles", ",".join(plex_roles))
    await interaction.response.send_message(f"Membarr will stop auto-adding \"{role.name}\" to Plex", ephemeral=True)


@plex_commands.command(name="listroles", description="List all roles whose members will be automatically added to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexrolels(interaction: discord.Interaction):
    await interaction.response.send_message(
        "The following roles are being automatically added to Plex:\n" +
        ", ".join(plex_roles), ephemeral=True
    )


@plex_commands.command(name="setup", description="Setup Plex integration")
@app_commands.checks.has_permissions(administrator=True)
async def setupplex(interaction: discord.Interaction, username: str, password: str, server_name: str,
                    base_url: str = "", save_token: bool = True):
    await interaction.response.defer()
    try:
        account = MyPlexAccount(username, password)
        plex = account.resource(server_name).connect()
    except Exception as e:
        if str(e).startswith("(429)"):
            await embederror(interaction.followup, "Too many requests. Please try again later.")
            return

        await embederror(interaction.followup, "Could not connect to Plex server. Please check your credentials.")
        return

    if (save_token):
        # Save new config entries
        confighelper.change_config("plex_base_url", plex._baseurl if base_url == "" else base_url)
        confighelper.change_config("plex_token", plex._token)
        confighelper.change_config("plex_server_name", server_name)

        # Delete old config entries
        confighelper.change_config("plex_user", "")
        confighelper.change_config("plex_pass", "")
    else:
        # Save new config entries
        confighelper.change_config("plex_user", username)
        confighelper.change_config("plex_pass", password)
        confighelper.change_config("plex_server_name", server_name)

        # Delete old config entries
        confighelper.change_config("plex_base_url", "")
        confighelper.change_config("plex_token", "")

    print("Plex authentication details updated. Restarting bot.")
    await interaction.followup.send(
        "Plex authentication details updated. Restarting bot. Please wait.\n" +
        "Please check logs and make sure you see the line: `Logged into plex`. If not run this command again and make sure you enter the right values.",
        ephemeral=True
    )
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@jellyfin_commands.command(name="addrole", description="Add a role to automatically add users to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def jellyroleadd(interaction: discord.Interaction, role: discord.Role):
    if len(jellyfin_roles) <= maxroles:
        # Do not add roles multiple times.
        if role.name in jellyfin_roles:
            await embederror(interaction.response, f"Jellyfin role \"{role.name}\" already added.")
            return

        jellyfin_roles.append(role.name)
        saveroles = ",".join(jellyfin_roles)
        confighelper.change_config("jellyfin_roles", saveroles)
        await interaction.response.send_message("Updated Jellyfin roles. Bot is restarting. Please wait a few seconds.",
                                                ephemeral=True)
        print("Jellyfin roles updated. Restarting bot.")
        await reload()
        print("Bot has been restarted. Give it a few seconds.")


@jellyfin_commands.command(name="removerole", description="Stop adding users with a role to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def jellyroleremove(interaction: discord.Interaction, role: discord.Role):
    if role.name not in jellyfin_roles:
        await embederror(interaction.response, f"\"{role.name}\" is currently not a Jellyfin role.")
        return
    jellyfin_roles.remove(role.name)
    confighelper.change_config("jellyfin_roles", ",".join(jellyfin_roles))
    await interaction.response.send_message(f"Membarr will stop auto-adding \"{role.name}\" to Jellyfin",
                                            ephemeral=True)


@jellyfin_commands.command(name="listroles",
                           description="List all roles whose members will be automatically added to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def jellyrolels(interaction: discord.Interaction):
    await interaction.response.send_message(
        "The following roles are being automatically added to Jellyfin:\n" +
        ", ".join(jellyfin_roles), ephemeral=True
    )


@jellyfin_commands.command(name="setup", description="Setup Jellyfin integration")
@app_commands.checks.has_permissions(administrator=True)
async def setupjelly(interaction: discord.Interaction, server_url: str, api_key: str, external_url: str = None):
    await interaction.response.defer()
    # get rid of training slashes
    server_url = server_url.rstrip('/')

    try:
        server_status = jelly.get_status(server_url, api_key)
        if server_status == 200:
            pass
        elif server_status == 401:
            # Unauthorized
            await embederror(interaction.followup, "API key provided is invalid")
            return
        elif server_status == 403:
            # Forbidden
            await embederror(interaction.followup, "API key provided does not have permissions")
            return
        elif server_status == 404:
            # page not found
            await embederror(interaction.followup, "Server endpoint provided was not found")
            return
        else:
            await embederror(interaction.followup,
                             "Unknown error occurred while connecting to Jellyfin. Check Membarr logs.")
    except ConnectTimeout as e:
        await embederror(interaction.followup,
                         "Connection to server timed out. Check that Jellyfin is online and reachable.")
        return
    except Exception as e:
        print("Exception while testing Jellyfin connection")
        print(type(e).__name__)
        print(e)
        await embederror(interaction.followup, "Unknown exception while connecting to Jellyfin. Check Membarr logs")
        return

    confighelper.change_config("jellyfin_server_url", str(server_url))
    confighelper.change_config("jellyfin_api_key", str(api_key))
    if external_url is not None:
        confighelper.change_config("jellyfin_external_url", str(external_url))
    else:
        confighelper.change_config("jellyfin_external_url", "")
    print("Jellyfin server URL and API key updated. Restarting bot.")
    await interaction.followup.send("Jellyfin server URL and API key updated. Restarting bot.", ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@plex_commands.command(name="setuplibs", description="Setup libraries that new users can access")
@app_commands.checks.has_permissions(administrator=True)
async def setupplexlibs(interaction: discord.Interaction, libraries: str):
    if not libraries:
        await embederror(interaction.response, "libraries string is empty.")
        return
    else:
        # Do some fancy python to remove spaces from libraries string, but only where wanted.
        libraries = ",".join(list(map(lambda lib: lib.strip(), libraries.split(","))))
        confighelper.change_config("plex_libs", str(libraries))
        print("Plex libraries updated. Restarting bot. Please wait.")
        await interaction.response.send_message("Plex libraries updated. Please wait a few seconds for bot to restart.",
                                                ephemeral=True)
        await reload()
        print("Bot has been restarted. Give it a few seconds.")


@jellyfin_commands.command(name="setuplibs", description="Setup libraries that new users can access")
@app_commands.checks.has_permissions(administrator=True)
async def setupjellylibs(interaction: discord.Interaction, libraries: str):
    if not libraries:
        await embederror(interaction.response, "libraries string is empty.")
        return
    else:
        # Do some fancy python to remove spaces from libraries string, but only where wanted.
        libraries = ",".join(list(map(lambda lib: lib.strip(), libraries.split(","))))
        confighelper.change_config("jellyfin_libs", str(libraries))
        print("Jellyfin libraries updated. Restarting bot. Please wait.")
        await interaction.response.send_message(
            "Jellyfin libraries updated. Please wait a few seconds for bot to restart.", ephemeral=True)
        await reload()
        print("Bot has been restarted. Give it a few seconds.")


# Enable / Disable Plex integration
@plex_commands.command(name="enable", description="Enable auto-adding users to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def enableplex(interaction: discord.Interaction):
    if confighelper.USE_PLEX:
        await interaction.response.send_message("Plex already enabled.", ephemeral=True)
        return
    confighelper.change_config("plex_enabled", True)
    print("Plex enabled, reloading server")
    await reload()
    confighelper.USE_PLEX = True
    await interaction.response.send_message("Plex enabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


@plex_commands.command(name="disable", description="Disable adding users to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def disableplex(interaction: discord.Interaction):
    if not confighelper.USE_PLEX:
        await interaction.response.send_message("Plex already disabled.", ephemeral=True)
        return
    confighelper.change_config("plex_enabled", False)
    print("Plex disabled, reloading server")
    await reload()
    confighelper.USE_PLEX = False
    await interaction.response.send_message("Plex disabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


# Enable / Disable Jellyfin integration
@jellyfin_commands.command(name="enable", description="Enable adding users to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def enablejellyfin(interaction: discord.Interaction):
    if confighelper.USE_JELLYFIN:
        await interaction.response.send_message("Jellyfin already enabled.", ephemeral=True)
        return
    confighelper.change_config("jellyfin_enabled", True)
    print("Jellyfin enabled, reloading server")
    confighelper.USE_JELLYFIN = True
    await reload()
    await interaction.response.send_message("Jellyfin enabled. Restarting server. Give it a few seconds.",
                                            ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


@jellyfin_commands.command(name="disable", description="Disable adding users to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def disablejellyfin(interaction: discord.Interaction):
    if not confighelper.USE_JELLYFIN:
        await interaction.response.send_message("Jellyfin already disabled.", ephemeral=True)
        return
    confighelper.change_config("jellyfin_enabled", False)
    print("Jellyfin disabled, reloading server")
    await reload()
    confighelper.USE_JELLYFIN = False
    await interaction.response.send_message("Jellyfin disabled. Restarting server. Give it a few seconds.",
                                            ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


@emby_commands.command(name="addrole", description="Add a role to automatically add users to Emby")
@app_commands.checks.has_permissions(administrator=True)
async def embyroleadd(interaction: discord.Interaction, role: discord.Role):
    if len(emby_roles) <= maxroles:
        if role.name in emby_roles:
            await embederror(interaction.response, f"Emby role \"{role.name}\" already added.")
            return
        emby_roles.append(role.name)
        saveroles = ",".join(emby_roles)
        confighelper.change_config("emby_roles", saveroles)
        await interaction.response.send_message("Updated Emby roles. Bot is restarting. Please wait.", ephemeral=True)
        print("Emby roles updated. Restarting bot.")
        await reload()
        print("Bot has been restarted. Give it a few seconds.")


@emby_commands.command(name="removerole", description="Stop adding users with a role to Emby")
@app_commands.checks.has_permissions(administrator=True)
async def embyroleremove(interaction: discord.Interaction, role: discord.Role):
    if role.name not in emby_roles:
        await embederror(interaction.response, f"\"{role.name}\" is currently not an Emby role.")
        return
    emby_roles.remove(role.name)
    confighelper.change_config("emby_roles", ",".join(emby_roles))
    await interaction.response.send_message(f"Membarr will stop auto-adding \"{role.name}\" to Emby", ephemeral=True)


@emby_commands.command(name="listroles", description="List all roles whose members will be automatically added to Emby")
@app_commands.checks.has_permissions(administrator=True)
async def embyrolels(interaction: discord.Interaction):
    await interaction.response.send_message(
        "The following roles are being automatically added to Emby:\n" +
        ", ".join(emby_roles), ephemeral=True
    )


@emby_commands.command(name="setup", description="Setup Emby integration")
@app_commands.checks.has_permissions(administrator=True)
async def setupemby(interaction: discord.Interaction, server_url: str, api_key: str, external_url: str = None):
    await interaction.response.defer()
    server_url = server_url.rstrip('/')

    try:
        server_status = emby.get_status(server_url, api_key)
        if server_status == 200:
            pass
        elif server_status == 401:
            await embederror(interaction.followup, "API key provided is invalid")
            return
        elif server_status == 403:
            await embederror(interaction.followup, "API key provided does not have permissions")
            return
        elif server_status == 404:
            await embederror(interaction.followup, "Server endpoint provided was not found")
            return
        else:
            await embederror(interaction.followup, "Unknown error occurred while connecting to Emby. Check Membarr logs.")
    except ConnectTimeout:
        await embederror(interaction.followup, "Connection to server timed out. Check that Emby is online and reachable.")
        return
    except Exception as e:
        print("Exception while testing Emby connection")
        print(type(e).__name__)
        print(e)
        await embederror(interaction.followup, "Unknown exception while connecting to Emby. Check Membarr logs")
        return

    confighelper.change_config("emby_server_url", str(server_url))
    confighelper.change_config("emby_api_key", str(api_key))
    if external_url is not None:
        confighelper.change_config("emby_external_url", str(external_url))
    else:
        confighelper.change_config("emby_external_url", "")
    print("Emby server URL and API key updated. Restarting bot.")
    await interaction.followup.send("Emby server URL and API key updated. Restarting bot.", ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@emby_commands.command(name="setuplibs", description="Setup libraries that new users can access")
@app_commands.checks.has_permissions(administrator=True)
async def setupembylibs(interaction: discord.Interaction, libraries: str):
    if not libraries:
        await embederror(interaction.response, "libraries string is empty.")
        return
    libraries = ",".join(list(map(lambda lib: lib.strip(), libraries.split(","))))
    confighelper.change_config("emby_libs", str(libraries))
    print("Emby libraries updated. Restarting bot. Please wait.")
    await interaction.response.send_message("Emby libraries updated. Please wait a few seconds for bot to restart.",
                                            ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@emby_commands.command(name="enable", description="Enable adding users to Emby")
@app_commands.checks.has_permissions(administrator=True)
async def enableemby(interaction: discord.Interaction):
    if confighelper.USE_EMBY:
        await interaction.response.send_message("Emby already enabled.", ephemeral=True)
        return
    confighelper.change_config("emby_enabled", True)
    print("Emby enabled, reloading server")
    confighelper.USE_EMBY = True
    await reload()
    await interaction.response.send_message("Emby enabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


@emby_commands.command(name="disable", description="Disable adding users to Emby")
@app_commands.checks.has_permissions(administrator=True)
async def disableemby(interaction: discord.Interaction):
    if not confighelper.USE_EMBY:
        await interaction.response.send_message("Emby already disabled.", ephemeral=True)
        return
    confighelper.change_config("emby_enabled", False)
    print("Emby disabled, reloading server")
    await reload()
    confighelper.USE_EMBY = False
    await interaction.response.send_message("Emby disabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


bot.tree.add_command(plex_commands)
bot.tree.add_command(jellyfin_commands)
bot.tree.add_command(emby_commands)

bot.run(Discord_bot_token)

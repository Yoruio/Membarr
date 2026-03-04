from pydoc import describe
import discord
import os
from discord.ext import commands, tasks
from discord.utils import get
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio
import sys
from app.bot.helper.confighelper import MEMBARR_VERSION, switch, Discord_bot_token, plex_roles
import app.bot.helper.confighelper as confighelper
import app.bot.helper.jellyfinhelper as jelly
import app.bot.helper.embyhelper as emby
import app.bot.helper.jellyseerrhelper as jellyseerr
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


# ── Autocomplete helpers ──────────────────────────────────────────────────────

async def jellyfin_server_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=s.name, value=s.name)
        for s in confighelper.jellyfin_servers
        if current.lower() in s.name.lower()
    ][:25]

async def emby_server_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=s.name, value=s.name)
        for s in confighelper.emby_servers
        if current.lower() in s.name.lower()
    ][:25]


# ── Command groups ────────────────────────────────────────────────────────────

plex_commands = app_commands.Group(name="plexsettings", description="Membarr Plex commands")
jellyfin_commands = app_commands.Group(name="jellyfinsettings", description="Membarr Jellyfin commands")
emby_commands = app_commands.Group(name="embysettings", description="Membarr Emby commands")


# ═══ Plex commands (unchanged) ════════════════════════════════════════════════

@plex_commands.command(name="addrole", description="Add a role to automatically add users to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexroleadd(interaction: discord.Interaction, role: discord.Role):
    if len(plex_roles) <= maxroles:
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
        confighelper.change_config("plex_base_url", plex._baseurl if base_url == "" else base_url)
        confighelper.change_config("plex_token", plex._token)
        confighelper.change_config("plex_server_name", server_name)
        confighelper.change_config("plex_user", "")
        confighelper.change_config("plex_pass", "")
    else:
        confighelper.change_config("plex_user", username)
        confighelper.change_config("plex_pass", password)
        confighelper.change_config("plex_server_name", server_name)
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


@plex_commands.command(name="setuplibs", description="Setup libraries that new users can access")
@app_commands.checks.has_permissions(administrator=True)
async def setupplexlibs(interaction: discord.Interaction, libraries: str):
    if not libraries:
        await embederror(interaction.response, "libraries string is empty.")
        return
    libraries = ",".join(list(map(lambda lib: lib.strip(), libraries.split(","))))
    confighelper.change_config("plex_libs", str(libraries))
    print("Plex libraries updated. Restarting bot. Please wait.")
    await interaction.response.send_message("Plex libraries updated. Please wait a few seconds for bot to restart.",
                                            ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


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


# ═══ Jellyfin commands (multi-server) ════════════════════════════════════════

@jellyfin_commands.command(name="setup", description="Add or update a Jellyfin server")
@app_commands.checks.has_permissions(administrator=True)
async def setupjelly(interaction: discord.Interaction, server_name: str, server_url: str, api_key: str,
                     external_url: str = None):
    await interaction.response.defer()
    server_url = server_url.rstrip('/')

    try:
        server_status = jelly.get_status(server_url, api_key)
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
            await embederror(interaction.followup,
                             "Unknown error occurred while connecting to Jellyfin. Check Membarr logs.")
            return
    except ConnectTimeout:
        await embederror(interaction.followup,
                         "Connection to server timed out. Check that Jellyfin is online and reachable.")
        return
    except Exception as e:
        print(f"Exception while testing Jellyfin connection: {type(e).__name__}: {e}")
        await embederror(interaction.followup, "Unknown exception while connecting to Jellyfin. Check Membarr logs")
        return

    section = f'jellyfin_{server_name}'
    confighelper.change_config("url", str(server_url), section=section)
    confighelper.change_config("api_key", str(api_key), section=section)
    confighelper.change_config("external_url", str(external_url) if external_url else "", section=section)
    confighelper.change_config("enabled", "true", section=section)

    # Add to server names list if not already there
    existing_names = [s.name for s in confighelper.jellyfin_servers]
    if server_name not in existing_names:
        existing_names.append(server_name)
    confighelper.change_config("jellyfin_server_names", ",".join(existing_names))

    print(f"Jellyfin server '{server_name}' configured. Restarting bot.")
    await interaction.followup.send(
        f"Jellyfin server **{server_name}** configured. Restarting bot. Please wait.", ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@jellyfin_commands.command(name="addrole", description="Add a role to automatically add users to a Jellyfin server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=jellyfin_server_autocomplete)
async def jellyroleadd(interaction: discord.Interaction, role: discord.Role, server_name: str):
    server = next((s for s in confighelper.jellyfin_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response,
                         f"Jellyfin server '{server_name}' not found. Run /jellyfinsettings setup first.")
        return
    if role.name in server.roles:
        await embederror(interaction.response, f"Role \"{role.name}\" is already added to **{server_name}**.")
        return
    if len(server.roles) >= maxroles:
        await embederror(interaction.response, "Maximum number of roles reached.")
        return

    server.roles.append(role.name)
    confighelper.change_config("roles", ",".join(server.roles), section=f"jellyfin_{server_name}")
    await interaction.response.send_message(
        f"Added role \"{role.name}\" to Jellyfin server **{server_name}**. Bot is restarting.", ephemeral=True)
    print(f"Jellyfin roles updated for {server_name}. Restarting bot.")
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@jellyfin_commands.command(name="removerole", description="Stop adding users with a role to a Jellyfin server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=jellyfin_server_autocomplete)
async def jellyroleremove(interaction: discord.Interaction, role: discord.Role, server_name: str):
    server = next((s for s in confighelper.jellyfin_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Jellyfin server '{server_name}' not found.")
        return
    if role.name not in server.roles:
        await embederror(interaction.response, f"\"{role.name}\" is not a role for **{server_name}**.")
        return
    server.roles.remove(role.name)
    confighelper.change_config("roles", ",".join(server.roles), section=f"jellyfin_{server_name}")
    await interaction.response.send_message(
        f"Membarr will stop auto-adding \"{role.name}\" to Jellyfin server **{server_name}**.", ephemeral=True)


@jellyfin_commands.command(name="listroles",
                           description="List roles for a Jellyfin server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=jellyfin_server_autocomplete)
async def jellyrolels(interaction: discord.Interaction, server_name: str):
    server = next((s for s in confighelper.jellyfin_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Jellyfin server '{server_name}' not found.")
        return
    roles_str = ", ".join(server.roles) if server.roles else "None"
    await interaction.response.send_message(
        f"Roles for Jellyfin **{server_name}**: {roles_str}", ephemeral=True)


@jellyfin_commands.command(name="setuplibs", description="Setup libraries accessible on a Jellyfin server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=jellyfin_server_autocomplete)
async def setupjellylibs(interaction: discord.Interaction, server_name: str, libraries: str):
    server = next((s for s in confighelper.jellyfin_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Jellyfin server '{server_name}' not found.")
        return
    if not libraries:
        await embederror(interaction.response, "Libraries string is empty.")
        return
    libraries = ",".join(lib.strip() for lib in libraries.split(","))
    confighelper.change_config("libs", str(libraries), section=f"jellyfin_{server_name}")
    print(f"Jellyfin libraries updated for {server_name}. Restarting bot.")
    await interaction.response.send_message(
        f"Jellyfin **{server_name}** libraries updated. Please wait a few seconds for bot to restart.",
        ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@jellyfin_commands.command(name="enable", description="Enable a Jellyfin server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=jellyfin_server_autocomplete)
async def enablejellyfin(interaction: discord.Interaction, server_name: str):
    server = next((s for s in confighelper.jellyfin_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Jellyfin server '{server_name}' not found.")
        return
    if server.enabled:
        await interaction.response.send_message(f"Jellyfin **{server_name}** is already enabled.", ephemeral=True)
        return
    confighelper.change_config("enabled", "true", section=f"jellyfin_{server_name}")
    server.enabled = True
    print(f"Jellyfin {server_name} enabled, reloading server")
    await interaction.response.send_message(
        f"Jellyfin **{server_name}** enabled. Restarting server. Give it a few seconds.", ephemeral=True)
    await reload()
    print("Bot has restarted. Give it a few seconds.")


@jellyfin_commands.command(name="disable", description="Disable a Jellyfin server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=jellyfin_server_autocomplete)
async def disablejellyfin(interaction: discord.Interaction, server_name: str):
    server = next((s for s in confighelper.jellyfin_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Jellyfin server '{server_name}' not found.")
        return
    if not server.enabled:
        await interaction.response.send_message(f"Jellyfin **{server_name}** is already disabled.", ephemeral=True)
        return
    confighelper.change_config("enabled", "false", section=f"jellyfin_{server_name}")
    server.enabled = False
    print(f"Jellyfin {server_name} disabled, reloading server")
    await interaction.response.send_message(
        f"Jellyfin **{server_name}** disabled. Restarting server. Give it a few seconds.", ephemeral=True)
    await reload()
    print("Bot has restarted. Give it a few seconds.")


@jellyfin_commands.command(name="list", description="List all configured Jellyfin servers")
@app_commands.checks.has_permissions(administrator=True)
async def jellylist(interaction: discord.Interaction):
    if not confighelper.jellyfin_servers:
        await interaction.response.send_message(
            "No Jellyfin servers configured. Use `/jellyfinsettings setup` to add one.", ephemeral=True)
        return
    lines = []
    for s in confighelper.jellyfin_servers:
        status = "✅ enabled" if s.enabled else "❌ disabled"
        roles_str = ", ".join(s.roles) if s.roles else "none"
        lines.append(f"**{s.name}** — {status}\n  URL: {s.url}\n  Roles: {roles_str}")
    await interaction.response.send_message("\n\n".join(lines), ephemeral=True)


# ═══ Emby commands (multi-server) ════════════════════════════════════════════

@emby_commands.command(name="setup", description="Add or update an Emby server")
@app_commands.checks.has_permissions(administrator=True)
async def setupemby(interaction: discord.Interaction, server_name: str, server_url: str, api_key: str,
                    external_url: str = None):
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
            return
    except ConnectTimeout:
        await embederror(interaction.followup, "Connection to server timed out. Check that Emby is online and reachable.")
        return
    except Exception as e:
        print(f"Exception while testing Emby connection: {type(e).__name__}: {e}")
        await embederror(interaction.followup, "Unknown exception while connecting to Emby. Check Membarr logs")
        return

    section = f'emby_{server_name}'
    confighelper.change_config("url", str(server_url), section=section)
    confighelper.change_config("api_key", str(api_key), section=section)
    confighelper.change_config("external_url", str(external_url) if external_url else "", section=section)
    confighelper.change_config("enabled", "true", section=section)

    existing_names = [s.name for s in confighelper.emby_servers]
    if server_name not in existing_names:
        existing_names.append(server_name)
    confighelper.change_config("emby_server_names", ",".join(existing_names))

    print(f"Emby server '{server_name}' configured. Restarting bot.")
    await interaction.followup.send(
        f"Emby server **{server_name}** configured. Restarting bot. Please wait.", ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@emby_commands.command(name="addrole", description="Add a role to automatically add users to an Emby server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=emby_server_autocomplete)
async def embyroleadd(interaction: discord.Interaction, role: discord.Role, server_name: str):
    server = next((s for s in confighelper.emby_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Emby server '{server_name}' not found. Run /embysettings setup first.")
        return
    if role.name in server.roles:
        await embederror(interaction.response, f"Role \"{role.name}\" is already added to **{server_name}**.")
        return
    if len(server.roles) >= maxroles:
        await embederror(interaction.response, "Maximum number of roles reached.")
        return

    server.roles.append(role.name)
    confighelper.change_config("roles", ",".join(server.roles), section=f"emby_{server_name}")
    await interaction.response.send_message(
        f"Added role \"{role.name}\" to Emby server **{server_name}**. Bot is restarting.", ephemeral=True)
    print(f"Emby roles updated for {server_name}. Restarting bot.")
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@emby_commands.command(name="removerole", description="Stop adding users with a role to an Emby server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=emby_server_autocomplete)
async def embyroleremove(interaction: discord.Interaction, role: discord.Role, server_name: str):
    server = next((s for s in confighelper.emby_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Emby server '{server_name}' not found.")
        return
    if role.name not in server.roles:
        await embederror(interaction.response, f"\"{role.name}\" is not a role for **{server_name}**.")
        return
    server.roles.remove(role.name)
    confighelper.change_config("roles", ",".join(server.roles), section=f"emby_{server_name}")
    await interaction.response.send_message(
        f"Membarr will stop auto-adding \"{role.name}\" to Emby server **{server_name}**.", ephemeral=True)


@emby_commands.command(name="listroles", description="List roles for an Emby server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=emby_server_autocomplete)
async def embyrolels(interaction: discord.Interaction, server_name: str):
    server = next((s for s in confighelper.emby_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Emby server '{server_name}' not found.")
        return
    roles_str = ", ".join(server.roles) if server.roles else "None"
    await interaction.response.send_message(
        f"Roles for Emby **{server_name}**: {roles_str}", ephemeral=True)


@emby_commands.command(name="setuplibs", description="Setup libraries accessible on an Emby server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=emby_server_autocomplete)
async def setupembylibs(interaction: discord.Interaction, server_name: str, libraries: str):
    server = next((s for s in confighelper.emby_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Emby server '{server_name}' not found.")
        return
    if not libraries:
        await embederror(interaction.response, "Libraries string is empty.")
        return
    libraries = ",".join(lib.strip() for lib in libraries.split(","))
    confighelper.change_config("libs", str(libraries), section=f"emby_{server_name}")
    print(f"Emby libraries updated for {server_name}. Restarting bot.")
    await interaction.response.send_message(
        f"Emby **{server_name}** libraries updated. Please wait a few seconds for bot to restart.", ephemeral=True)
    await reload()
    print("Bot has been restarted. Give it a few seconds.")


@emby_commands.command(name="enable", description="Enable an Emby server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=emby_server_autocomplete)
async def enableemby(interaction: discord.Interaction, server_name: str):
    server = next((s for s in confighelper.emby_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Emby server '{server_name}' not found.")
        return
    if server.enabled:
        await interaction.response.send_message(f"Emby **{server_name}** is already enabled.", ephemeral=True)
        return
    confighelper.change_config("enabled", "true", section=f"emby_{server_name}")
    server.enabled = True
    print(f"Emby {server_name} enabled, reloading server")
    await interaction.response.send_message(
        f"Emby **{server_name}** enabled. Restarting server. Give it a few seconds.", ephemeral=True)
    await reload()
    print("Bot has restarted. Give it a few seconds.")


@emby_commands.command(name="disable", description="Disable an Emby server")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(server_name=emby_server_autocomplete)
async def disableemby(interaction: discord.Interaction, server_name: str):
    server = next((s for s in confighelper.emby_servers if s.name == server_name), None)
    if server is None:
        await embederror(interaction.response, f"Emby server '{server_name}' not found.")
        return
    if not server.enabled:
        await interaction.response.send_message(f"Emby **{server_name}** is already disabled.", ephemeral=True)
        return
    confighelper.change_config("enabled", "false", section=f"emby_{server_name}")
    server.enabled = False
    print(f"Emby {server_name} disabled, reloading server")
    await interaction.response.send_message(
        f"Emby **{server_name}** disabled. Restarting server. Give it a few seconds.", ephemeral=True)
    await reload()
    print("Bot has restarted. Give it a few seconds.")


@emby_commands.command(name="list", description="List all configured Emby servers")
@app_commands.checks.has_permissions(administrator=True)
async def embylist(interaction: discord.Interaction):
    if not confighelper.emby_servers:
        await interaction.response.send_message(
            "No Emby servers configured. Use `/embysettings setup` to add one.", ephemeral=True)
        return
    lines = []
    for s in confighelper.emby_servers:
        status = "✅ enabled" if s.enabled else "❌ disabled"
        roles_str = ", ".join(s.roles) if s.roles else "none"
        lines.append(f"**{s.name}** — {status}\n  URL: {s.url}\n  Roles: {roles_str}")
    await interaction.response.send_message("\n\n".join(lines), ephemeral=True)



# ═══ Jellyseerr settings commands ════════════════════════════════════════════

jellyseerr_commands = app_commands.Group(name="jellyseerrsettings",
                                         description="Membarr Jellyseerr settings")


@jellyseerr_commands.command(name="setup",
                             description="Configure Jellyseerr integration")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.autocomplete(jellyfin_server=jellyfin_server_autocomplete)
async def setupjellyseerr(interaction: discord.Interaction, url: str, api_key: str,
                          jellyfin_server: str = ""):
    """Set Jellyseerr URL and API key.

    jellyfin_server: name of the Jellyfin server whose usernames will be used
    to match Discord users to their Jellyseerr accounts. Leave blank if only
    one Jellyfin server is configured.
    """
    await interaction.response.defer()
    url = url.rstrip('/')
    try:
        status = jellyseerr.get_status(url, api_key)
        if status != 200:
            await embederror(interaction.followup,
                             f"Could not connect to Jellyseerr (HTTP {status}). Check URL and API key.")
            return
    except Exception as e:
        print(f"Jellyseerr connection error: {e}")
        await embederror(interaction.followup,
                         "Could not reach Jellyseerr. Check that it is online and reachable.")
        return

    confighelper.change_config("jellyseerr_url", url)
    confighelper.change_config("jellyseerr_api_key", api_key)
    confighelper.change_config("jellyseerr_jellyfin_server", jellyfin_server)
    confighelper.JELLYSEERR_URL = url
    confighelper.JELLYSEERR_API_KEY = api_key
    confighelper.JELLYSEERR_JELLYFIN_SERVER = jellyfin_server
    confighelper.jellyseerr_configured = True

    print("Jellyseerr configured. Restarting bot.")
    await interaction.followup.send("Jellyseerr configured successfully. Restarting bot.", ephemeral=True)
    await reload()


@jellyseerr_commands.command(name="status", description="Show current Jellyseerr configuration")
@app_commands.checks.has_permissions(administrator=True)
async def jellyseerrstatus(interaction: discord.Interaction):
    if not confighelper.jellyseerr_configured:
        await interaction.response.send_message(
            "Jellyseerr is not configured. Use `/jellyseerrsettings setup` first.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"**Jellyseerr** configured:\n"
        f"  URL: {confighelper.JELLYSEERR_URL}\n"
        f"  Jellyfin server: {confighelper.JELLYSEERR_JELLYFIN_SERVER or '(first configured)'}",
        ephemeral=True
    )


bot.tree.add_command(plex_commands)
bot.tree.add_command(jellyfin_commands)
bot.tree.add_command(emby_commands)
bot.tree.add_command(jellyseerr_commands)

bot.run(Discord_bot_token)

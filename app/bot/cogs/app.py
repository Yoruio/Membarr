import configparser
import app.bot.helper.jellyfinhelper as jelly
from app.bot.helper.textformat import bcolors
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import app.bot.helper.db as db
import app.bot.helper.plexhelper as plexhelper
import app.bot.helper.jellyfinhelper as jelly
import app.bot.helper.embyhelper as embyhelper
import app.bot.helper.jellyseerrhelper as jellyseerr
import texttable
from app.bot.helper.message import *
import app.bot.helper.confighelper as confighelper
from app.bot.helper.confighelper import (
    MEMBARR_VERSION, ServerConfig, load_servers,
    USE_PLEX, plex_configured, plex_roles, Plex_LIBS, PLEX_SERVER_NAME,
)

CONFIG_PATH = 'app/config/config.ini'
BOT_SECTION = 'bot_envs'

# Re-read config fresh on every cog load/reload
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

# Load per-server lists fresh from disk
jellyfin_servers = load_servers(config, 'jellyfin')
emby_servers = load_servers(config, 'emby')

# Jellyseerr config
JELLYSEERR_URL = ""
JELLYSEERR_API_KEY = ""
JELLYSEERR_JELLYFIN_SERVER = ""
jellyseerr_configured = False
try:
    JELLYSEERR_URL = config.get(BOT_SECTION, 'jellyseerr_url').rstrip('/')
    JELLYSEERR_API_KEY = config.get(BOT_SECTION, 'jellyseerr_api_key')
    JELLYSEERR_JELLYFIN_SERVER = config.get(BOT_SECTION, 'jellyseerr_jellyfin_server')
    jellyseerr_configured = bool(JELLYSEERR_URL and JELLYSEERR_API_KEY)
except:
    pass

# Plex config (still single-server)
plex_configured = True
plex_token_configured = True
try:
    PLEX_TOKEN = config.get(BOT_SECTION, 'plex_token')
    PLEX_BASE_URL = config.get(BOT_SECTION, 'plex_base_url')
except:
    print("No Plex auth token details found")
    plex_token_configured = False

try:
    PLEXUSER = config.get(BOT_SECTION, 'plex_user')
    PLEXPASS = config.get(BOT_SECTION, 'plex_pass')
    PLEX_SERVER_NAME = config.get(BOT_SECTION, 'plex_server_name')
except:
    print("No Plex login info found")
    if not plex_token_configured:
        print("Could not load plex config")
        plex_configured = False

try:
    plex_roles = config.get(BOT_SECTION, 'plex_roles')
except:
    plex_roles = None
if plex_roles:
    plex_roles = list(plex_roles.split(','))
else:
    plex_roles = []

try:
    Plex_LIBS = config.get(BOT_SECTION, 'plex_libs')
except:
    Plex_LIBS = None
if Plex_LIBS is None:
    Plex_LIBS = ["all"]
else:
    Plex_LIBS = list(Plex_LIBS.split(','))

try:
    USE_PLEX = config.get(BOT_SECTION, "plex_enabled")
    USE_PLEX = USE_PLEX.lower() == "true"
except:
    USE_PLEX = False

if USE_PLEX and plex_configured:
    try:
        print("Connecting to Plex......")
        if plex_token_configured and PLEX_TOKEN and PLEX_BASE_URL:
            print("Using Plex auth token")
            plex = PlexServer(PLEX_BASE_URL, PLEX_TOKEN)
        else:
            print("Using Plex login info")
            account = MyPlexAccount(PLEXUSER, PLEXPASS)
            plex = account.resource(PLEX_SERVER_NAME).connect()
        print('Logged into plex!')
    except Exception as e:
        print('Error with plex login. Please check Plex authentication details. If you have restarted the bot multiple times recently, this is most likely due to being ratelimited on the Plex API. Try again in 10 minutes.')
        print(f'Error: {e}')
else:
    print(f"Plex {'disabled' if not USE_PLEX else 'not configured'}. Skipping Plex login.")


# ── Autocomplete helpers ──────────────────────────────────────────────────────

async def jellyfin_server_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=s.name, value=s.name)
        for s in jellyfin_servers
        if current.lower() in s.name.lower()
    ][:25]

async def emby_server_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=s.name, value=s.name)
        for s in emby_servers
        if current.lower() in s.name.lower()
    ][:25]


# ── Server selection UI for /register with multiple servers ───────────────────

class JellyfinServerSelect(discord.ui.Select):
    def __init__(self, servers: list):
        options = [discord.SelectOption(label=s.name, value=s.name) for s in servers]
        super().__init__(placeholder="Choose a Jellyfin server...", options=options)
        self.servers_by_name = {s.name: s for s in servers}

    async def callback(self, interaction: discord.Interaction):
        server = self.servers_by_name[self.values[0]]
        await interaction.response.send_modal(JellyfinRegisterModal(server))


class JellyfinServerSelectView(discord.ui.View):
    def __init__(self, servers: list):
        super().__init__(timeout=60)
        self.add_item(JellyfinServerSelect(servers))


class EmbyServerSelect(discord.ui.Select):
    def __init__(self, servers: list):
        options = [discord.SelectOption(label=s.name, value=s.name) for s in servers]
        super().__init__(placeholder="Choose an Emby server...", options=options)
        self.servers_by_name = {s.name: s for s in servers}

    async def callback(self, interaction: discord.Interaction):
        server = self.servers_by_name[self.values[0]]
        await interaction.response.send_modal(EmbyRegisterModal(server))


class EmbyServerSelectView(discord.ui.View):
    def __init__(self, servers: list):
        super().__init__(timeout=60)
        self.add_item(EmbyServerSelect(servers))


# ── Modals ────────────────────────────────────────────────────────────────────

class EmbyRegisterModal(discord.ui.Modal, title="Link Emby Account"):
    username = discord.ui.TextInput(label="Emby Username", required=True, max_length=100)
    password = discord.ui.TextInput(label="Password", required=True, max_length=200, style=discord.TextStyle.short)

    def __init__(self, server: ServerConfig):
        super().__init__(title=f"Link Emby Account — {server.name}")
        self.server = server

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        username = self.username.value
        password = self.password.value
        success = await asyncio.to_thread(embyhelper.authenticate_user, self.server.url, username, password)
        if success:
            db.save_server_account(str(interaction.user.id), 'emby', self.server.name, username)
            await interaction.followup.send(
                f"Your Emby account **{username}** has been linked to your Discord account on **{self.server.name}**.",
                ephemeral=True)
        else:
            await interaction.followup.send("Invalid credentials. Please check your Emby username and password.",
                                            ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(error)
        await interaction.followup.send("Something went wrong. Please try again later.", ephemeral=True)


class JellyfinRegisterModal(discord.ui.Modal, title="Link Jellyfin Account"):
    username = discord.ui.TextInput(label="Jellyfin Username", required=True, max_length=100)
    password = discord.ui.TextInput(label="Password", required=True, max_length=200, style=discord.TextStyle.short)

    def __init__(self, server: ServerConfig):
        super().__init__(title=f"Link Jellyfin Account — {server.name}")
        self.server = server

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        username = self.username.value
        password = self.password.value
        success = await asyncio.to_thread(jelly.authenticate_user, self.server.url, username, password)
        if success:
            db.save_server_account(str(interaction.user.id), 'jellyfin', self.server.name, username)
            await interaction.followup.send(
                f"Your Jellyfin account **{username}** has been linked to your Discord account on **{self.server.name}**.",
                ephemeral=True)
        else:
            await interaction.followup.send("Invalid credentials. Please check your Jellyfin username and password.",
                                            ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(error)
        await interaction.followup.send("Something went wrong. Please try again later.", ephemeral=True)


class PlexRegisterModal(discord.ui.Modal, title="Link Plex Account"):
    username = discord.ui.TextInput(label="Plex Username or Email", required=True, max_length=200)
    password = discord.ui.TextInput(label="Password", required=True, max_length=200, style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        username = self.username.value
        password = self.password.value
        try:
            email = await asyncio.to_thread(plexhelper.authenticate_user, username, password)
            db.save_user_email(str(interaction.user.id), email)
            await interaction.followup.send("Your Plex account has been linked to your Discord account.",
                                            ephemeral=True)
        except Exception as e:
            err = str(e)
            if "401" in err or "Unauthorized" in err.lower():
                await interaction.followup.send(
                    "Invalid credentials. Please check your Plex username/email and password.", ephemeral=True)
            else:
                await interaction.followup.send("Could not reach the Plex server. Please try again later.",
                                                ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(error)
        await interaction.followup.send("Something went wrong. Please try again later.", ephemeral=True)


# ── Main cog ──────────────────────────────────────────────────────────────────

class app(commands.Cog):
    plex_commands = app_commands.Group(name="plex", description="Membarr Plex commands")
    jellyfin_commands = app_commands.Group(name="jellyfin", description="Membarr Jellyfin commands")
    membarr_commands = app_commands.Group(name="membarr", description="Membarr general commands")
    emby_commands = app_commands.Group(name="emby", description="Membarr Emby commands")
    register_commands = app_commands.Group(name="register", description="Link your media server account to Discord")
    request_commands = app_commands.Group(name="request", description="Browse and manage Jellyseerr media requests")

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('------')
        print("{:^41}".format(f"MEMBARR V {MEMBARR_VERSION}"))
        print(f'Made by Yoruio https://github.com/Yoruio/\n')
        print(f'Forked from Invitarr https://github.com/Sleepingpirates/Invitarr')
        print(f'Named by lordfransie')
        print(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
        print('------')

        enabled_jf = [s.name for s in jellyfin_servers if s.enabled]
        enabled_emby = [s.name for s in emby_servers if s.enabled]
        if not plex_roles:
            print('Configure Plex roles to enable auto invite to Plex after a role is assigned.')
        if not enabled_jf:
            print('No enabled Jellyfin servers. Use /jellyfinsettings setup to configure one.')
        if not enabled_emby:
            print('No enabled Emby servers. Use /embysettings setup to configure one.')

    # ── DM prompt helpers ─────────────────────────────────────────────────────

    async def getemail(self, after):
        email = None
        await embedinfo(after, 'Welcome To ' + PLEX_SERVER_NAME + '. Please reply with your email to be added to the Plex server!')
        await embedinfo(after, 'If you do not respond within 24 hours, the request will be cancelled, and the server admin will need to add you manually.')
        while email is None:
            def check(m):
                return m.author == after and not m.guild
            try:
                email = await self.bot.wait_for('message', timeout=86400, check=check)
                if plexhelper.verifyemail(str(email.content)):
                    return str(email.content)
                else:
                    email = None
                    await embederror(after, "The email you provided is invalid, please respond only with the email you used to sign up for Plex.")
            except asyncio.TimeoutError:
                await embederror(after, "Timed out. Please contact the server admin directly.")
                return None

    async def getusername(self, after, server: ServerConfig):
        username = None
        await embedinfo(after, f"Welcome To **{server.name}**! Please reply with your desired username for the Jellyfin server.")
        await embedinfo(after, "If you do not respond within 24 hours, the request will be cancelled, and the server admin will need to add you manually.")
        while username is None:
            def check(m):
                return m.author == after and not m.guild
            try:
                username = await self.bot.wait_for('message', timeout=86400, check=check)
                if jelly.verify_username(server.url, server.api_key, str(username.content)):
                    return str(username.content)
                else:
                    username = None
                    await embederror(after, "This username is already taken. Please select another username.")
            except asyncio.TimeoutError:
                await embederror(after, "Timed out. Please contact the server admin directly.")
                print("Jellyfin user prompt timed out")
                return None
            except Exception as e:
                await embederror(after, "Something went wrong. Please try again with another username.")
                print(e)
                username = None

    async def getembyusername(self, after, server: ServerConfig):
        username = None
        await embedinfo(after, f"Welcome To **{server.name}**! Please reply with your desired Emby username.")
        await embedinfo(after, "If you do not respond within 24 hours, the request will be cancelled.")
        while username is None:
            def check(m):
                return m.author == after and not m.guild
            try:
                username = await self.bot.wait_for('message', timeout=86400, check=check)
                if embyhelper.verify_username(server.url, server.api_key, str(username.content)):
                    return str(username.content)
                else:
                    username = None
                    await embederror(after, "This username is already taken. Please choose another.")
            except asyncio.TimeoutError:
                await embederror(after, "Timed out. Please contact the server admin directly.")
                return None
            except Exception as e:
                await embederror(after, "Something went wrong. Please try again with another username.")
                print(e)
                username = None

    async def getpassword(self, after, server_name: str):
        await embedinfo(after, f"Please reply with the password you'd like to use for **{server_name}**.")
        def check(m):
            return m.author == after and not m.guild
        try:
            msg = await self.bot.wait_for('message', timeout=86400, check=check)
            return str(msg.content)
        except asyncio.TimeoutError:
            await embederror(after, "Timed out. Please contact the server admin directly.")
            return None

    # ── Server action helpers ─────────────────────────────────────────────────

    async def addtoplex(self, email, response):
        if plexhelper.verifyemail(email):
            if plexhelper.plexadd(plex, email, Plex_LIBS):
                await embedinfo(response, 'This email address has been added to plex')
                return True
            else:
                await embederror(response, 'There was an error adding this email address. Check logs.')
                return False
        else:
            await embederror(response, 'Invalid email.')
            return False

    async def removefromplex(self, email, response):
        if plexhelper.verifyemail(email):
            if plexhelper.plexremove(plex, email):
                await embedinfo(response, 'This email address has been removed from plex.')
                return True
            else:
                await embederror(response, 'There was an error removing this email address. Check logs.')
                return False
        else:
            await embederror(response, 'Invalid email.')
            return False

    async def addtojellyfin(self, username, password, server: ServerConfig, response):
        if not jelly.verify_username(server.url, server.api_key, username):
            await embederror(response, f'An account with username {username} already exists on **{server.name}**.')
            return False
        if jelly.add_user(server.url, server.api_key, username, password, server.libs):
            return True
        else:
            await embederror(response, f'There was an error adding this user to **{server.name}**. Check logs for more info.')
            return False

    async def removefromjellyfin(self, username, server: ServerConfig, response):
        if jelly.verify_username(server.url, server.api_key, username):
            await embederror(response, f'Could not find account with username {username} on **{server.name}**.')
            return False
        if jelly.remove_user(server.url, server.api_key, username):
            await embedinfo(response, f'Successfully removed user {username} from **{server.name}**.')
            return True
        else:
            await embederror(response, f'There was an error removing this user from **{server.name}**. Check logs for more info.')
            return False

    async def addtoemby(self, username, password, server: ServerConfig, response):
        if not embyhelper.verify_username(server.url, server.api_key, username):
            await embederror(response, f'An account with username {username} already exists on **{server.name}**.')
            return False
        if embyhelper.add_user(server.url, server.api_key, username, password, server.libs):
            return True
        else:
            await embederror(response, f'There was an error adding this user to **{server.name}**. Check logs for more info.')
            return False

    async def removefromemby(self, username, server: ServerConfig, response):
        if embyhelper.verify_username(server.url, server.api_key, username):
            await embederror(response, f'Could not find account with username {username} on **{server.name}**.')
            return False
        if embyhelper.remove_user(server.url, server.api_key, username):
            await embedinfo(response, f'Successfully removed user {username} from **{server.name}**.')
            return True
        else:
            await embederror(response, f'There was an error removing this user from **{server.name}**. Check logs for more info.')
            return False

    # ── Event listeners ───────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        roles_in_guild = {r.name: r for r in after.guild.roles}

        # ── Plex ──
        if plex_configured and USE_PLEX:
            plex_processed = False
            for role_name in plex_roles:
                role = roles_in_guild.get(role_name)
                if role is None:
                    continue
                if role in after.roles and role not in before.roles:
                    email = await self.getemail(after)
                    if email is not None:
                        await embedinfo(after, "Got it we will be adding your email to plex shortly!")
                        if plexhelper.plexadd(plex, email, Plex_LIBS):
                            db.save_user_email(str(after.id), email)
                            await asyncio.sleep(5)
                            await embedinfo(after, 'You have Been Added To Plex! Login to plex and accept the invite!')
                        else:
                            await embedinfo(after, 'There was an error adding this email address. Message Server Admin.')
                    plex_processed = True
                    break
                elif role not in after.roles and role in before.roles:
                    try:
                        email = db.get_useremail(after.id)
                        plexhelper.plexremove(plex, email)
                        db.remove_email(after.id)
                        await embedinfo(after, "You have been removed from Plex")
                    except Exception as e:
                        print(e)
                    plex_processed = True
                    break

        # ── Jellyfin servers ──
        for server in jellyfin_servers:
            if not server.enabled:
                continue
            jf_processed = False
            for role_name in server.roles:
                role = roles_in_guild.get(role_name)
                if role is None:
                    continue
                if role in after.roles and role not in before.roles:
                    print(f"Jellyfin role added for server {server.name}")
                    username = await self.getusername(after, server)
                    password = None
                    if username is not None:
                        password = await self.getpassword(after, server.name)
                    if username is not None and password is not None:
                        await embedinfo(after, f"Got it, we will be creating your **{server.name}** account shortly!")
                        if jelly.add_user(server.url, server.api_key, username, password, server.libs):
                            db.save_server_account(str(after.id), 'jellyfin', server.name, username)
                            await asyncio.sleep(5)
                            login_url = server.external_url or server.url
                            await embedinfo(after, f"You have been added to **{server.name}**! Go to {login_url} to log in.")
                        else:
                            await embedinfo(after, f'There was an error adding you to **{server.name}**. Message Server Admin.')
                    jf_processed = True
                    break
                elif role not in after.roles and role in before.roles:
                    print(f"Jellyfin role removed for server {server.name}")
                    try:
                        username = db.get_server_account(str(after.id), 'jellyfin', server.name)
                        if username:
                            jelly.remove_user(server.url, server.api_key, username)
                            db.remove_server_account(str(after.id), 'jellyfin', server.name)
                            print(f"Removed {after.name} from Jellyfin {server.name}")
                        await embedinfo(after, f"You have been removed from **{server.name}**")
                    except Exception as e:
                        print(e)
                    jf_processed = True
                    break

        # ── Emby servers ──
        for server in emby_servers:
            if not server.enabled:
                continue
            emby_processed = False
            for role_name in server.roles:
                role = roles_in_guild.get(role_name)
                if role is None:
                    continue
                if role in after.roles and role not in before.roles:
                    print(f"Emby role added for server {server.name}")
                    username = await self.getembyusername(after, server)
                    password = None
                    if username is not None:
                        password = await self.getpassword(after, server.name)
                    if username is not None and password is not None:
                        await embedinfo(after, f"Got it, we will be creating your **{server.name}** account shortly!")
                        if embyhelper.add_user(server.url, server.api_key, username, password, server.libs):
                            db.save_server_account(str(after.id), 'emby', server.name, username)
                            await asyncio.sleep(5)
                            login_url = server.external_url or server.url
                            await embedinfo(after, f"You have been added to **{server.name}**! Go to {login_url} to log in.")
                        else:
                            await embedinfo(after, f'There was an error adding you to **{server.name}**. Message Server Admin.')
                    emby_processed = True
                    break
                elif role not in after.roles and role in before.roles:
                    print(f"Emby role removed for server {server.name}")
                    try:
                        username = db.get_server_account(str(after.id), 'emby', server.name)
                        if username:
                            embyhelper.remove_user(server.url, server.api_key, username)
                            db.remove_server_account(str(after.id), 'emby', server.name)
                            print(f"Removed {after.name} from Emby {server.name}")
                        await embedinfo(after, f"You have been removed from **{server.name}**")
                    except Exception as e:
                        print(e)
                    emby_processed = True
                    break

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if USE_PLEX and plex_configured:
            email = db.get_useremail(member.id)
            plexhelper.plexremove(plex, email)

        for server in jellyfin_servers:
            if not server.enabled:
                continue
            username = db.get_server_account(str(member.id), 'jellyfin', server.name)
            if username:
                jelly.remove_user(server.url, server.api_key, username)

        for server in emby_servers:
            if not server.enabled:
                continue
            username = db.get_server_account(str(member.id), 'emby', server.name)
            if username:
                embyhelper.remove_user(server.url, server.api_key, username)

        deleted = db.delete_user(member.id)
        if deleted:
            print("Removed {} from db because user left discord server.".format(member.name))

    # ── Admin invite/remove commands ──────────────────────────────────────────

    @app_commands.checks.has_permissions(administrator=True)
    @plex_commands.command(name="invite", description="Invite a user to Plex")
    async def plexinvite(self, interaction: discord.Interaction, email: str):
        await self.addtoplex(email, interaction.response)

    @app_commands.checks.has_permissions(administrator=True)
    @plex_commands.command(name="remove", description="Remove a user from Plex")
    async def plexremove(self, interaction: discord.Interaction, email: str):
        await self.removefromplex(email, interaction.response)

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(server_name=jellyfin_server_autocomplete)
    @jellyfin_commands.command(name="invite", description="Invite a user to a Jellyfin server")
    async def jellyfininvite(self, interaction: discord.Interaction, username: str, server_name: str):
        server = next((s for s in jellyfin_servers if s.name == server_name), None)
        if server is None:
            await embederror(interaction.response, f"Jellyfin server '{server_name}' not found.")
            return
        password = jelly.generate_password(16)
        if await self.addtojellyfin(username, password, server, interaction.response):
            await embedcustom(interaction.response, f"Jellyfin user created on **{server.name}**!",
                              {'Username': username, 'Password': f"||{password}||"})

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(server_name=jellyfin_server_autocomplete)
    @jellyfin_commands.command(name="remove", description="Remove a user from a Jellyfin server")
    async def jellyfinremove(self, interaction: discord.Interaction, username: str, server_name: str):
        server = next((s for s in jellyfin_servers if s.name == server_name), None)
        if server is None:
            await embederror(interaction.response, f"Jellyfin server '{server_name}' not found.")
            return
        await self.removefromjellyfin(username, server, interaction.response)

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(server_name=emby_server_autocomplete)
    @emby_commands.command(name="invite", description="Invite a user to an Emby server")
    async def embyinvite(self, interaction: discord.Interaction, username: str, server_name: str):
        server = next((s for s in emby_servers if s.name == server_name), None)
        if server is None:
            await embederror(interaction.response, f"Emby server '{server_name}' not found.")
            return
        password = embyhelper.generate_password(16)
        if await self.addtoemby(username, password, server, interaction.response):
            await embedcustom(interaction.response, f"Emby user created on **{server.name}**!",
                              {'Username': username, 'Password': f"||{password}||"})

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(server_name=emby_server_autocomplete)
    @emby_commands.command(name="remove", description="Remove a user from an Emby server")
    async def embyremove(self, interaction: discord.Interaction, username: str, server_name: str):
        server = next((s for s in emby_servers if s.name == server_name), None)
        if server is None:
            await embederror(interaction.response, f"Emby server '{server_name}' not found.")
            return
        await self.removefromemby(username, server, interaction.response)

    # ── Membarr DB commands ───────────────────────────────────────────────────

    @app_commands.checks.has_permissions(administrator=True)
    @membarr_commands.command(name="dbadd", description="Add a user to the Membarr database")
    async def dbadd(self, interaction: discord.Interaction, member: discord.Member, email: str = ""):
        email = email.strip()
        if email and not plexhelper.verifyemail(email):
            await embederror(interaction.response, "Invalid email.")
            return
        try:
            if email:
                db.save_user_email(str(member.id), email)
            else:
                db.save_user(str(member.id))
            await embedinfo(interaction.response, 'User was added to the database.')
        except Exception as e:
            await embedinfo(interaction.response, 'There was an error adding this user to database. Check Membarr logs for more info')
            print(e)

    @app_commands.checks.has_permissions(administrator=True)
    @membarr_commands.command(name="dbls", description="View Membarr database")
    async def dbls(self, interaction: discord.Interaction):
        embed = discord.Embed(title='Membarr Database.')
        all_users = db.read_all()
        table = texttable.Texttable()
        table.set_cols_dtype(["t", "t", "t", "t"])
        table.set_cols_align(["c", "c", "c", "c"])
        header = ("#", "Name", "Plex Email", "Server Accounts")
        table.add_row(header)

        for index, row in enumerate(all_users):
            index = index + 1
            discord_id = int(row[1])
            plex_email = row[2] if row[2] else "No Plex"
            server_accounts = row[3]  # list of (server_type, server_name, username)
            accounts_str = ", ".join(f"{sa[0]}/{sa[1]}:{sa[2]}" for sa in server_accounts) if server_accounts else "None"

            dbuser = self.bot.get_user(discord_id)
            try:
                username = dbuser.name
            except:
                username = "User Not Found."

            embed.add_field(name=f"**{index}. {username}**",
                            value=f"{plex_email}\n{accounts_str}\n", inline=False)
            table.add_row((index, username, plex_email, accounts_str))

        total = str(len(all_users))
        if len(all_users) > 25:
            f = open("db.txt", "w")
            f.write(table.draw())
            f.close()
            await interaction.response.send_message(
                f"Database too large! Total: {total}", file=discord.File('db.txt'), ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.checks.has_permissions(administrator=True)
    @membarr_commands.command(name="dbrm", description="Remove user from Membarr database")
    async def dbrm(self, interaction: discord.Interaction, position: int):
        all_users = db.read_all()
        try:
            position = int(position) - 1
            discord_id = all_users[position][1]
            discord_user = await self.bot.fetch_user(int(discord_id))
            username = discord_user.name
            deleted = db.delete_user(discord_id)
            if deleted:
                print(f"Removed {username} from db")
                await embedinfo(interaction.response, f"Removed {username} from db")
            else:
                await embederror(interaction.response, "Cannot remove this user from db.")
        except Exception as e:
            print(e)
            await embederror(interaction.response, "Error removing user from db.")

    # ── Register commands ─────────────────────────────────────────────────────

    @register_commands.command(name="jellyfin", description="Link your existing Jellyfin account to Discord")
    async def register_jellyfin(self, interaction: discord.Interaction):
        enabled_servers = [s for s in jellyfin_servers if s.enabled]
        if not enabled_servers:
            await interaction.response.send_message("Jellyfin is not enabled on this server.", ephemeral=True)
            return
        if len(enabled_servers) == 1:
            await interaction.response.send_modal(JellyfinRegisterModal(enabled_servers[0]))
        else:
            view = JellyfinServerSelectView(enabled_servers)
            await interaction.response.send_message("Select a Jellyfin server to link:", view=view, ephemeral=True)

    @register_commands.command(name="plex", description="Link your existing Plex account to Discord")
    async def register_plex(self, interaction: discord.Interaction):
        if not USE_PLEX or not plex_configured:
            await interaction.response.send_message("Plex is not enabled on this server.", ephemeral=True)
            return
        await interaction.response.send_modal(PlexRegisterModal())

    @register_commands.command(name="emby", description="Link your existing Emby account to Discord")
    async def register_emby(self, interaction: discord.Interaction):
        enabled_servers = [s for s in emby_servers if s.enabled]
        if not enabled_servers:
            await interaction.response.send_message("Emby is not enabled on this server.", ephemeral=True)
            return
        if len(enabled_servers) == 1:
            await interaction.response.send_modal(EmbyRegisterModal(enabled_servers[0]))
        else:
            view = EmbyServerSelectView(enabled_servers)
            await interaction.response.send_message("Select an Emby server to link:", view=view, ephemeral=True)

    # ── Jellyseerr request commands ───────────────────────────────────────────

    def _get_jellyseerr_server_name(self) -> str:
        """Return the Jellyfin server name configured for Jellyseerr user matching."""
        if JELLYSEERR_JELLYFIN_SERVER:
            return JELLYSEERR_JELLYFIN_SERVER
        # Default: first enabled Jellyfin server
        for s in jellyfin_servers:
            if s.enabled:
                return s.name
        return jellyfin_servers[0].name if jellyfin_servers else ""

    def _require_jellyseerr(self, interaction: discord.Interaction):
        """Return True if Jellyseerr is configured, else send error and return False."""
        return jellyseerr_configured

    @request_commands.command(name="list", description="Show your pending and recent Jellyseerr requests")
    async def request_list(self, interaction: discord.Interaction):
        if not jellyseerr_configured:
            await interaction.response.send_message(
                "Jellyseerr is not configured on this server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Find the user's Jellyfin username
        server_name = self._get_jellyseerr_server_name()
        jf_username = db.get_server_account(str(interaction.user.id), 'jellyfin', server_name)
        if not jf_username:
            await interaction.followup.send(
                f"You don't have a Jellyfin account linked on **{server_name}**. "
                f"Use `/register jellyfin` to link your account first.", ephemeral=True)
            return

        # Find the Jellyseerr user
        js_user = await asyncio.to_thread(
            jellyseerr.find_user_by_jellyfin_username, JELLYSEERR_URL, JELLYSEERR_API_KEY, jf_username)
        if not js_user:
            await interaction.followup.send(
                f"Could not find your account in Jellyseerr. Make sure you have logged in to "
                f"Jellyseerr at least once with your Jellyfin account.", ephemeral=True)
            return

        requests_list = await asyncio.to_thread(
            jellyseerr.get_user_requests, JELLYSEERR_URL, JELLYSEERR_API_KEY, js_user['id'])

        if not requests_list:
            await interaction.followup.send("You have no requests in Jellyseerr.", ephemeral=True)
            return

        embed = discord.Embed(title="Your Jellyseerr Requests", color=discord.Color.blue())
        for req in requests_list[:10]:
            media = req.get('media', {})
            title = media.get('originalTitle') or media.get('id', 'Unknown')
            media_type = jellyseerr.format_media_type(req.get('type', ''))
            status = jellyseerr.format_status(req.get('status', 0))
            year = media.get('releaseDate', '')[:4] if media.get('releaseDate') else ''
            label = f"{title} ({year})" if year else title
            embed.add_field(name=f"{media_type} — {label}", value=status, inline=False)

        if len(requests_list) > 10:
            embed.set_footer(text=f"Showing 10 of {len(requests_list)} requests")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @request_commands.command(name="search", description="Search for a movie or TV show on Jellyseerr")
    async def request_search(self, interaction: discord.Interaction, query: str):
        if not jellyseerr_configured:
            await interaction.response.send_message(
                "Jellyseerr is not configured on this server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        results = await asyncio.to_thread(
            jellyseerr.search, JELLYSEERR_URL, JELLYSEERR_API_KEY, query)

        if not results:
            await interaction.followup.send(f"No results found for **{query}**.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Jellyseerr Search: {query}",
            description="Use `/request movie` or `/request tv` with the title to submit a request.",
            color=discord.Color.green()
        )
        for result in results[:8]:
            media_type = jellyseerr.format_media_type(result.get('mediaType', ''))
            title = result.get('title') or result.get('name', 'Unknown')
            year_raw = result.get('releaseDate') or result.get('firstAirDate', '')
            year = year_raw[:4] if year_raw else ''
            overview = result.get('overview', '')[:100] + '...' if len(result.get('overview', '')) > 100 else result.get('overview', '')
            media_info = result.get('mediaInfo')
            avail = " ✅ Available" if media_info and media_info.get('status') == 5 else ""
            embed.add_field(
                name=f"{media_type} — {title} ({year}){avail}",
                value=overview or "No description.",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @request_commands.command(name="pending",
                              description="[Admin] List all pending Jellyseerr requests")
    @app_commands.checks.has_permissions(administrator=True)
    async def request_pending(self, interaction: discord.Interaction):
        if not jellyseerr_configured:
            await interaction.response.send_message(
                "Jellyseerr is not configured on this server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        pending = await asyncio.to_thread(
            jellyseerr.get_all_requests, JELLYSEERR_URL, JELLYSEERR_API_KEY, "pending", 20)

        if not pending:
            await interaction.followup.send("No pending requests.", ephemeral=True)
            return

        view = PendingRequestsView(pending, JELLYSEERR_URL, JELLYSEERR_API_KEY)
        embed = _build_pending_embed(pending)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


def _build_pending_embed(pending: list) -> discord.Embed:
    embed = discord.Embed(title="Pending Jellyseerr Requests", color=discord.Color.orange())
    for i, req in enumerate(pending[:10]):
        media = req.get('media', {})
        title = media.get('originalTitle') or media.get('id', 'Unknown')
        media_type = jellyseerr.format_media_type(req.get('type', ''))
        requestedBy = req.get('requestedBy', {})
        requester = requestedBy.get('displayName', 'Unknown')
        year_raw = media.get('releaseDate') or media.get('firstAirDate', '')
        year = year_raw[:4] if year_raw else ''
        label = f"{title} ({year})" if year else title
        embed.add_field(
            name=f"{i + 1}. {media_type} — {label}",
            value=f"Requested by: {requester} | ID: {req['id']}",
            inline=False
        )
    return embed


class ApproveButton(discord.ui.Button):
    def __init__(self, request_id: int, url: str, api_key: str):
        super().__init__(label=f"Approve #{request_id}", style=discord.ButtonStyle.green,
                         custom_id=f"approve_{request_id}")
        self.request_id = request_id
        self.url = url
        self.api_key = api_key

    async def callback(self, interaction: discord.Interaction):
        success = await asyncio.to_thread(
            jellyseerr.approve_request, self.url, self.api_key, self.request_id)
        if success:
            await interaction.response.send_message(
                f"Request #{self.request_id} approved.", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"Failed to approve request #{self.request_id}.", ephemeral=True)


class DeclineButton(discord.ui.Button):
    def __init__(self, request_id: int, url: str, api_key: str):
        super().__init__(label=f"Decline #{request_id}", style=discord.ButtonStyle.red,
                         custom_id=f"decline_{request_id}")
        self.request_id = request_id
        self.url = url
        self.api_key = api_key

    async def callback(self, interaction: discord.Interaction):
        success = await asyncio.to_thread(
            jellyseerr.decline_request, self.url, self.api_key, self.request_id)
        if success:
            await interaction.response.send_message(
                f"Request #{self.request_id} declined.", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"Failed to decline request #{self.request_id}.", ephemeral=True)


class PendingRequestsView(discord.ui.View):
    def __init__(self, pending: list, url: str, api_key: str):
        super().__init__(timeout=120)
        # Add approve/decline buttons for first 4 requests (Discord max 25 buttons, 5 per row)
        for req in pending[:4]:
            rid = req['id']
            self.add_item(ApproveButton(rid, url, api_key))
            self.add_item(DeclineButton(rid, url, api_key))


async def setup(bot):
    await bot.add_cog(app(bot))

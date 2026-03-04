import configparser
import os
from dataclasses import dataclass, field
from os import environ, path
from typing import List
from dotenv import load_dotenv

CONFIG_PATH = 'app/config/config.ini'
BOT_SECTION = 'bot_envs'
MEMBARR_VERSION = 1.2

config = configparser.ConfigParser()

CONFIG_KEYS = ['username', 'password', 'discord_bot_token', 'plex_user', 'plex_pass', 'plex_token',
                'plex_base_url', 'plex_roles', 'plex_server_name', 'plex_libs', 'owner_id', 'channel_id',
                'auto_remove_user', 'plex_enabled',
                'jellyfin_server_names', 'emby_server_names']

@dataclass
class ServerConfig:
    name: str
    url: str
    api_key: str
    external_url: str
    roles: List[str]
    libs: List[str]
    enabled: bool


# ── Token loading ─────────────────────────────────────────────────────────────

Discord_bot_token = ""
switch = 0

if(path.exists('bot.env')):
    try:
        load_dotenv(dotenv_path='bot.env')
        Discord_bot_token = environ.get('discord_bot_token')
        switch = 1
    except Exception as e:
        pass

try:
    Discord_bot_token = str(os.environ['token'])
    switch = 1
except Exception as e:
    pass

if not (path.exists(CONFIG_PATH)):
    with open(CONFIG_PATH, 'w') as fp:
        pass

config = configparser.ConfigParser()
config.read(CONFIG_PATH)


# ── Server loading ────────────────────────────────────────────────────────────

def load_servers(cfg: configparser.ConfigParser, server_type: str) -> List[ServerConfig]:
    """Load all server configs for a given type ('jellyfin' or 'emby').

    First tries the new per-server format ([jellyfin_{name}] sections).
    Falls back to the old flat keys (jellyfin_server_url, etc.) if not found.
    """
    servers = []
    try:
        names_str = cfg.get(BOT_SECTION, f'{server_type}_server_names')
        names = [n.strip() for n in names_str.split(',') if n.strip()]
        for name in names:
            section = f'{server_type}_{name}'
            try:
                url = cfg.get(section, 'url').rstrip('/')
                api_key = cfg.get(section, 'api_key')
                external_url = ''
                try:
                    external_url = cfg.get(section, 'external_url') or url
                except:
                    external_url = url
                roles_str = ''
                try:
                    roles_str = cfg.get(section, 'roles')
                except:
                    pass
                roles = [r.strip() for r in roles_str.split(',') if r.strip()]
                libs_str = 'all'
                try:
                    libs_str = cfg.get(section, 'libs') or 'all'
                except:
                    pass
                libs = [l.strip() for l in libs_str.split(',') if l.strip()] or ['all']
                enabled_str = 'false'
                try:
                    enabled_str = cfg.get(section, 'enabled')
                except:
                    pass
                enabled = enabled_str.strip().lower() == 'true'
                servers.append(ServerConfig(name, url, api_key, external_url, roles, libs, enabled))
            except Exception as e:
                print(f"Could not load {server_type} server config for '{name}': {e}")
        return servers
    except:
        pass

    # Fallback: read old flat-config keys
    try:
        url = cfg.get(BOT_SECTION, f'{server_type}_server_url').rstrip('/')
        api_key = cfg.get(BOT_SECTION, f'{server_type}_api_key')
        external_url = url
        try:
            external_url = cfg.get(BOT_SECTION, f'{server_type}_external_url') or url
        except:
            pass
        roles_str = ''
        try:
            roles_str = cfg.get(BOT_SECTION, f'{server_type}_roles')
        except:
            pass
        roles = [r.strip() for r in roles_str.split(',') if r.strip()]
        libs_str = 'all'
        try:
            libs_str = cfg.get(BOT_SECTION, f'{server_type}_libs') or 'all'
        except:
            pass
        libs = [l.strip() for l in libs_str.split(',') if l.strip()] or ['all']
        enabled_str = 'false'
        try:
            enabled_str = cfg.get(BOT_SECTION, f'{server_type}_enabled')
        except:
            pass
        enabled = enabled_str.strip().lower() == 'true'
        default_name = 'Jellyfin' if server_type == 'jellyfin' else 'Emby'
        servers.append(ServerConfig(default_name, url, api_key, external_url, roles, libs, enabled))
    except Exception as e:
        print(f"Could not load {server_type} config: {e}")

    return servers


jellyfin_servers: List[ServerConfig] = load_servers(config, 'jellyfin')
emby_servers: List[ServerConfig] = load_servers(config, 'emby')


# ── Backward-compat single-server variables (from first server in each list) ──

jellyfin_configured = bool(jellyfin_servers)
USE_JELLYFIN = jellyfin_servers[0].enabled if jellyfin_servers else False
JELLYFIN_SERVER_URL = jellyfin_servers[0].url if jellyfin_servers else ""
JELLYFIN_API_KEY = jellyfin_servers[0].api_key if jellyfin_servers else ""
JELLYFIN_EXTERNAL_URL = jellyfin_servers[0].external_url if jellyfin_servers else ""
jellyfin_roles = jellyfin_servers[0].roles if jellyfin_servers else []
jellyfin_libs = jellyfin_servers[0].libs if jellyfin_servers else ["all"]

emby_configured = bool(emby_servers)
USE_EMBY = emby_servers[0].enabled if emby_servers else False
EMBY_SERVER_URL = emby_servers[0].url if emby_servers else ""
EMBY_API_KEY = emby_servers[0].api_key if emby_servers else ""
EMBY_EXTERNAL_URL = emby_servers[0].external_url if emby_servers else ""
emby_roles = emby_servers[0].roles if emby_servers else []
emby_libs = emby_servers[0].libs if emby_servers else ["all"]


# ── Jellyseerr ────────────────────────────────────────────────────────────────

JELLYSEERR_URL = ""
JELLYSEERR_API_KEY = ""
JELLYSEERR_JELLYFIN_SERVER = ""  # which Jellyfin server name to use for user matching
jellyseerr_configured = False

try:
    JELLYSEERR_URL = config.get(BOT_SECTION, 'jellyseerr_url').rstrip('/')
    JELLYSEERR_API_KEY = config.get(BOT_SECTION, 'jellyseerr_api_key')
    JELLYSEERR_JELLYFIN_SERVER = config.get(BOT_SECTION, 'jellyseerr_jellyfin_server')
    jellyseerr_configured = bool(JELLYSEERR_URL and JELLYSEERR_API_KEY)
except:
    print("Could not load Jellyseerr config")


# ── Plex (unchanged) ──────────────────────────────────────────────────────────

plex_configured = True

plex_token_configured = True
try:
    PLEX_TOKEN = config.get(BOT_SECTION, 'plex_token')
    PLEX_BASE_URL = config.get(BOT_SECTION, 'plex_base_url')
except:
    print("No Plex auth token details found")
    plex_token_configured = False

try:
    PLEX_SERVER_NAME = config.get(BOT_SECTION, 'plex_server_name')
    PLEXUSER = config.get(BOT_SECTION, 'plex_user')
    PLEXPASS = config.get(BOT_SECTION, 'plex_pass')
except:
    print("No Plex login info found")
    if not plex_token_configured:
        print("Could not load plex config")
        plex_configured = False

try:
    plex_roles = config.get(BOT_SECTION, 'plex_roles')
except:
    print("Could not get Plex roles config")
    plex_roles = None
if plex_roles:
    plex_roles = list(plex_roles.split(','))
else:
    plex_roles = []

try:
    Plex_LIBS = config.get(BOT_SECTION, 'plex_libs')
except:
    print("Could not get Plex libs config. Defaulting to all libraries.")
    Plex_LIBS = None
if Plex_LIBS is None:
    Plex_LIBS = ["all"]
else:
    Plex_LIBS = list(Plex_LIBS.split(','))

try:
    USE_PLEX = config.get(BOT_SECTION, "plex_enabled")
    USE_PLEX = USE_PLEX.lower() == "true"
except:
    print("Could not get Plex enable config. Defaulting to False")
    USE_PLEX = False


# ── Config helpers ────────────────────────────────────────────────────────────

def get_config():
    """Return current config."""
    try:
        config.read(CONFIG_PATH)
        return config
    except Exception as e:
        print(e)
        print('error in reading config')
        return None


def change_config(key, value, section=BOT_SECTION):
    """Write a key/value pair to the given config section."""
    try:
        cfg = configparser.ConfigParser()
        cfg.read(CONFIG_PATH)
    except Exception as e:
        print(e)
        print("Cannot Read config.")
        return

    try:
        cfg.set(section, key, str(value))
    except configparser.NoSectionError:
        cfg.add_section(section)
        cfg.set(section, key, str(value))

    try:
        with open(CONFIG_PATH, 'w') as configfile:
            cfg.write(configfile)
    except Exception as e:
        print(e)
        print("Cannot write to config.")

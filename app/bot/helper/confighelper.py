import configparser
import os
from os import environ, path
from dotenv import load_dotenv

CONFIG_PATH = 'app/config/config.ini'
BOT_SECTION = 'bot_envs'
MEMBARR_VERSION = 1.1

config = configparser.ConfigParser()

CONFIG_KEYS = ['username', 'password', 'discord_bot_token', 'plex_user', 'plex_pass', 'plex_token',
                'plex_base_url', 'plex_roles', 'plex_server_name', 'plex_libs', 'owner_id', 'channel_id',
                'auto_remove_user', 'jellyfin_api_key', 'jellyfin_server_url', 'jellyfin_roles',
                'jellyfin_libs', 'plex_enabled', 'jellyfin_enabled', 'jellyfin_external_url',
                'emby_api_key', 'emby_server_url', 'emby_roles', 'emby_libs', 'emby_enabled',
                'emby_external_url']

# settings
Discord_bot_token = ""
plex_roles = None
PLEXUSER = ""
PLEXPASS = ""
PLEX_SERVER_NAME = ""
PLEX_TOKEN = ""
PLEX_BASE_URL = ""
Plex_LIBS = None
JELLYFIN_SERVER_URL = ""
JELLYFIN_API_KEY = ""
jellyfin_libs = ""
jellyfin_roles = None
plex_configured = True
jellyfin_configured = True
EMBY_SERVER_URL = ""
EMBY_API_KEY = ""
EMBY_EXTERNAL_URL = ""
emby_libs = ""
emby_roles = None
emby_configured = True
USE_EMBY = False

switch = 0 

# TODO: make this into a class

if(path.exists('bot.env')):
    try:
        load_dotenv(dotenv_path='bot.env')
        # settings
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
    with open (CONFIG_PATH, 'w') as fp:
        pass



config = configparser.ConfigParser()
config.read(CONFIG_PATH)

plex_token_configured = True
try:
    PLEX_TOKEN = config.get(BOT_SECTION, 'plex_token')
    PLEX_BASE_URL = config.get(BOT_SECTION, 'plex_base_url')
except:
    print("No Plex auth token details found")
    plex_token_configured = False

# Get Plex config
try:
    PLEX_SERVER_NAME = config.get(BOT_SECTION, 'plex_server_name')
    PLEXUSER = config.get(BOT_SECTION, 'plex_user')
    PLEXPASS = config.get(BOT_SECTION, 'plex_pass')
except:
    print("No Plex login info found")
    if not plex_token_configured:
        print("Could not load plex config")
        plex_configured = False

# Get Plex roles config
try:
    plex_roles = config.get(BOT_SECTION, 'plex_roles')
except:
    print("Could not get Plex roles config")
    plex_roles = None
if plex_roles:
    plex_roles = list(plex_roles.split(','))
else:
    plex_roles = []

# Get Plex libs config
try:
    Plex_LIBS = config.get(BOT_SECTION, 'plex_libs')
except:
    print("Could not get Plex libs config. Defaulting to all libraries.")
    Plex_LIBS = None
if Plex_LIBS is None:
    Plex_LIBS = ["all"]
else:
    Plex_LIBS = list(Plex_LIBS.split(','))
    
# Get Jellyfin config
try:
    JELLYFIN_SERVER_URL = config.get(BOT_SECTION, 'jellyfin_server_url')
    JELLYFIN_API_KEY = config.get(BOT_SECTION, "jellyfin_api_key")
except:
    print("Could not load Jellyfin config")
    jellyfin_configured = False

try:
    JELLYFIN_EXTERNAL_URL = config.get(BOT_SECTION, "jellyfin_external_url")
    if not JELLYFIN_EXTERNAL_URL:
        JELLYFIN_EXTERNAL_URL = JELLYFIN_SERVER_URL
except:
    JELLYFIN_EXTERNAL_URL = JELLYFIN_SERVER_URL
    print("Could not get Jellyfin external url. Defaulting to server url.")

# Get Jellyfin roles config
try:
    jellyfin_roles = config.get(BOT_SECTION, 'jellyfin_roles')
except:
    print("Could not get Jellyfin roles config")
    jellyfin_roles = None
if jellyfin_roles:
    jellyfin_roles = list(jellyfin_roles.split(','))
else:
    jellyfin_roles = []

# Get Jellyfin libs config
try:
    jellyfin_libs = config.get(BOT_SECTION, 'jellyfin_libs')
except:
    print("Could not get Jellyfin libs config. Defaulting to all libraries.")
    jellyfin_libs = None
if jellyfin_libs is None:
    jellyfin_libs = ["all"]
else:
    jellyfin_libs = list(jellyfin_libs.split(','))

# Get Enable config
try:
    USE_JELLYFIN = config.get(BOT_SECTION, 'jellyfin_enabled')
    USE_JELLYFIN = USE_JELLYFIN.lower() == "true"
except:
    print("Could not get Jellyfin enable config. Defaulting to False")
    USE_JELLYFIN = False

try:
    USE_PLEX = config.get(BOT_SECTION, "plex_enabled")
    USE_PLEX = USE_PLEX.lower() == "true"
except:
    print("Could not get Plex enable config. Defaulting to False")
    USE_PLEX = False

# Get Emby config
try:
    EMBY_SERVER_URL = config.get(BOT_SECTION, 'emby_server_url')
    EMBY_API_KEY = config.get(BOT_SECTION, "emby_api_key")
except:
    print("Could not load Emby config")
    emby_configured = False

try:
    EMBY_EXTERNAL_URL = config.get(BOT_SECTION, "emby_external_url")
    if not EMBY_EXTERNAL_URL:
        EMBY_EXTERNAL_URL = EMBY_SERVER_URL
except:
    EMBY_EXTERNAL_URL = EMBY_SERVER_URL
    print("Could not get Emby external url. Defaulting to server url.")

# Get Emby roles config
try:
    emby_roles = config.get(BOT_SECTION, 'emby_roles')
except:
    print("Could not get Emby roles config")
    emby_roles = None
if emby_roles:
    emby_roles = list(emby_roles.split(','))
else:
    emby_roles = []

# Get Emby libs config
try:
    emby_libs = config.get(BOT_SECTION, 'emby_libs')
except:
    print("Could not get Emby libs config. Defaulting to all libraries.")
    emby_libs = None
if emby_libs is None:
    emby_libs = ["all"]
else:
    emby_libs = list(emby_libs.split(','))

try:
    USE_EMBY = config.get(BOT_SECTION, 'emby_enabled')
    USE_EMBY = USE_EMBY.lower() == "true"
except:
    print("Could not get Emby enable config. Defaulting to False")
    USE_EMBY = False

def get_config():
    """
    Function to return current config
    """
    try:
        config.read(CONFIG_PATH)
        return config
    except Exception as e:
        print(e)
        print('error in reading config')
        return None


def change_config(key, value):
    """
    Function to change the key, value pair in config
    """
    try:
        config = configparser.ConfigParser()
        config.read(CONFIG_PATH)
    except Exception as e:
        print(e)
        print("Cannot Read config.")

    try:
        config.set(BOT_SECTION, key, str(value))
    except Exception as e:
        config.add_section(BOT_SECTION)
        config.set(BOT_SECTION, key, str(value))

    try:
        with open(CONFIG_PATH, 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        print(e)
        print("Cannot write to config.")

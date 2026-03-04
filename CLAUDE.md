# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Membarr is a Discord bot that automatically manages Plex and Jellyfin media server memberships based on Discord role assignments. When a user receives a configured role, the bot invites them to the media server via DM; when the role is removed or the user leaves, they are kicked.

## Running the Bot

```bash
# Local (bare Python)
pip3 install -r requirements.txt
python3 run.py   # requires discord_bot_token set in bot.env

# Docker
docker run -d --restart unless-stopped --name membarr \
  -v /path/to/config:/app/app/config \
  -e "token=YOUR_DISCORD_TOKEN_HERE" \
  yoruio/membarr:latest
```

There is no test suite, linter configuration, or Makefile.

## Architecture

### Entry Point (`run.py`)

1. `confighelper.py` loads at import time — reads `bot.env` (or `os.environ['token']`) and `app/config/config.ini`.
2. Registers two `app_commands.Group` objects (`/plexsettings`, `/jellyfinsettings`) directly on the bot.
3. Loads the `app.bot.cogs.app` extension which holds all other slash commands and event listeners.
4. After any settings change, `await reload()` calls `bot.reload_extension('app.bot.cogs.app')` to re-read config from disk and reconnect to Plex if needed.

### Core Cog (`app/bot/cogs/app.py`)

All Discord event listeners and user-facing commands live here:
- `on_member_update`: detects role add/remove → triggers invite or kick
- `on_member_remove`: kicks user from Plex/Jellyfin when they leave the guild
- `/plex invite|remove`, `/jellyfin invite|remove`, `/membarr dbls|dbadd|dbrm`

The cog re-reads `config.ini` and reconnects to Plex on every reload.

### Auto-Invite Flow

```
Role assigned → on_member_update
  → DM user asking for email (Plex) or username (Jellyfin)
  → Wait up to 24 hours for DM reply
  → Call plexhelper/jellyfinhelper to create the account
  → Save discord_user_id + credential to SQLite
  → DM user confirmation (Jellyfin includes auto-generated password)
```

### Helpers

| File | Responsibility |
|---|---|
| `confighelper.py` | Read/write `config.ini` via `configparser`; load token from env |
| `db.py` | All SQLite operations on `app/config/app.db` (`clients` table) |
| `dbupdater.py` | One-time schema migration from Invitarr V1.0 format |
| `jellyfinhelper.py` | Jellyfin REST API calls via `requests` |
| `plexhelper.py` | Plex API calls via `plexapi` library |
| `message.py` | Discord embed builders (error, info, custom) |

### Persistent Storage

Both files live in `app/config/` (Docker volume mount):
- `config.ini` — all bot settings (`[bot_envs]` section); written by `confighelper.change_config()`
- `app.db` — SQLite; `clients` table stores `discord_username` (actually the Discord user ID), `email` (Plex), `jellyfin_username`

### Discord Bot Requirements

All three Privileged Gateway Intents must be enabled in the Discord Developer Portal: Presence Intent, Server Members Intent, Message Content Intent. The OAuth2 URL must include both `bot` and `applications.commands` scopes.

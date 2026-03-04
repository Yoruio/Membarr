"""
Shared helpers for the web UI.

Uses its own SQLite connections (not db.py) to avoid triggering migrations
in the web process and to keep clean separation from the bot's module state.
Config reads always go to disk; writes use confighelper.change_config().
"""

import configparser
import sqlite3
from typing import Optional, List, Tuple

CONFIG_PATH = 'app/config/config.ini'
DB_PATH = 'app/config/app.db'
BOT_SECTION = 'bot_envs'


# ── Config ────────────────────────────────────────────────────────────────────

def read_config() -> configparser.ConfigParser:
    """Return a freshly-read ConfigParser instance."""
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return cfg


def write_config(key: str, value: str, section: str = BOT_SECTION):
    """Write a single key/value pair to config.ini."""
    from app.bot.helper.confighelper import change_config
    change_config(key, value, section)


def delete_server_config(server_type: str, server_name: str):
    """Remove a server's config section and its name from the names list."""
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    section = f'{server_type}_{server_name}'
    if cfg.has_section(section):
        cfg.remove_section(section)
    names_key = f'{server_type}_server_names'
    try:
        names = [n.strip() for n in cfg.get(BOT_SECTION, names_key).split(',') if n.strip()]
        names = [n for n in names if n != server_name]
        cfg.set(BOT_SECTION, names_key, ','.join(names))
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    with open(CONFIG_PATH, 'w') as f:
        cfg.write(f)


def get_server_config(cfg: configparser.ConfigParser, server_type: str, server_name: str) -> dict:
    """Return a dict of settings for a named server section."""
    section = f'{server_type}_{server_name}'
    defaults = {'name': server_name, 'url': '', 'api_key': '', 'external_url': '',
                'roles': '', 'libs': 'all', 'enabled': False}
    if not cfg.has_section(section):
        return defaults
    return {
        'name': server_name,
        'url': cfg.get(section, 'url', fallback=''),
        'api_key': cfg.get(section, 'api_key', fallback=''),
        'external_url': cfg.get(section, 'external_url', fallback=''),
        'roles': cfg.get(section, 'roles', fallback=''),
        'libs': cfg.get(section, 'libs', fallback='all'),
        'enabled': cfg.get(section, 'enabled', fallback='false').lower() == 'true',
    }


def list_server_names(cfg: configparser.ConfigParser, server_type: str) -> List[str]:
    """Return list of configured server names for a type."""
    try:
        raw = cfg.get(BOT_SECTION, f'{server_type}_server_names')
        return [n.strip() for n in raw.split(',') if n.strip()]
    except (configparser.NoSectionError, configparser.NoOptionError):
        return []


def save_server_config(server_type: str, server_name: str, data: dict):
    """Write all fields for a named server section and update the names list."""
    section = f'{server_type}_{server_name}'
    for key, value in data.items():
        write_config(key, str(value), section=section)
    # Add to names list if not already present
    cfg = read_config()
    existing = list_server_names(cfg, server_type)
    if server_name not in existing:
        existing.append(server_name)
    write_config(f'{server_type}_server_names', ','.join(existing))


# ── Database ──────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    """Open a fresh SQLite connection with WAL mode."""
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def db_read_all_users(conn: sqlite3.Connection) -> List[Tuple]:
    """Return (id, discord_id, email, [(server_type, server_name, username)])."""
    cur = conn.cursor()
    cur.execute("SELECT id, discord_id, email FROM clients ORDER BY id")
    rows = cur.fetchall()
    result = []
    for row in rows:
        cur2 = conn.cursor()
        cur2.execute(
            "SELECT server_type, server_name, username FROM server_accounts WHERE discord_id=? ORDER BY server_type, server_name",
            (row['discord_id'],)
        )
        accounts = cur2.fetchall()
        result.append((row['id'], row['discord_id'], row['email'], accounts))
    return result


def db_delete_user(conn: sqlite3.Connection, discord_id: str):
    conn.execute("DELETE FROM clients WHERE discord_id=?", (discord_id,))
    conn.execute("DELETE FROM server_accounts WHERE discord_id=?", (discord_id,))
    conn.commit()


def db_get_stats(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM clients")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM server_accounts WHERE server_type='jellyfin'")
    jf_accounts = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM server_accounts WHERE server_type='emby'")
    emby_accounts = cur.fetchone()[0]
    return {
        'total_users': total_users,
        'jellyfin_accounts': jf_accounts,
        'emby_accounts': emby_accounts,
    }


# ── Flash messages ────────────────────────────────────────────────────────────

def flash(request, message: str, category: str = 'success'):
    request.session['flash'] = {'message': message, 'category': category}


def pop_flash(request) -> Optional[dict]:
    return request.session.pop('flash', None)

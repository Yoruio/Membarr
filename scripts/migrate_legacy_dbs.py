#!/usr/bin/env python3
"""
migrate_legacy_dbs.py — One-time import of legacy jellyfin.db / emby.db data
into the new app/config/app.db with the V1.4 schema.

Usage:
    python3 scripts/migrate_legacy_dbs.py \
        --jellyfin-db jellyfin.db  --jellyfin-name MainJellyfin \
        --emby-db     emby.db      --emby-name     MainEmby \
        --output      app/config/app.db

The legacy DBs use the Membarr V1.1 schema:
    (id, discord_username, email, jellyfin_username)
where discord_username is actually the Discord user ID, and
jellyfin_username holds the media-server username (even in emby.db).
"""

import argparse
import sqlite3
import sys
import os


V14_CLIENTS_DDL = '''
CREATE TABLE IF NOT EXISTS "clients" (
    "id"         INTEGER NOT NULL UNIQUE,
    "discord_id" TEXT NOT NULL UNIQUE,
    "email"      TEXT,
    PRIMARY KEY("id" AUTOINCREMENT)
);
'''

SERVER_ACCOUNTS_DDL = '''
CREATE TABLE IF NOT EXISTS "server_accounts" (
    "id"          INTEGER PRIMARY KEY AUTOINCREMENT,
    "discord_id"  TEXT NOT NULL,
    "server_type" TEXT NOT NULL,
    "server_name" TEXT NOT NULL,
    "username"    TEXT NOT NULL,
    UNIQUE("discord_id", "server_type", "server_name")
);
'''


def open_legacy(path):
    """Open a legacy DB and return its rows as list of dicts."""
    if not os.path.exists(path):
        print(f"  [SKIP] {path} not found.")
        return []
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM clients")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def migrate(args):
    output = args.output
    print(f"\nTarget DB: {output}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output) if os.path.dirname(output) else '.', exist_ok=True)

    dest = sqlite3.connect(output)
    dest.execute(V14_CLIENTS_DDL)
    dest.execute(SERVER_ACCOUNTS_DDL)
    dest.commit()

    jf_imported = 0
    emby_imported = 0
    plex_imported = 0

    # ── Jellyfin ──
    if args.jellyfin_db:
        print(f"\nReading Jellyfin legacy DB: {args.jellyfin_db}")
        rows = open_legacy(args.jellyfin_db)
        print(f"  Found {len(rows)} rows.")
        for row in rows:
            # Legacy column is 'discord_username' (actually the discord user ID)
            discord_id = str(row.get('discord_username') or row.get('discord_id') or '').strip()
            media_username = str(row.get('jellyfin_username') or '').strip()
            email = str(row.get('email') or '').strip() or None

            if not discord_id:
                continue

            # Upsert into clients
            dest.execute(
                "INSERT OR IGNORE INTO clients(discord_id, email) VALUES(?, ?)",
                (discord_id, email)
            )
            if email:
                dest.execute(
                    "UPDATE clients SET email=? WHERE discord_id=? AND email IS NULL",
                    (email, discord_id)
                )
                plex_imported += 1

            if media_username:
                dest.execute(
                    "INSERT OR IGNORE INTO server_accounts(discord_id, server_type, server_name, username) VALUES(?, ?, ?, ?)",
                    (discord_id, 'jellyfin', args.jellyfin_name, media_username)
                )
                jf_imported += 1

        dest.commit()

    # ── Emby ──
    if args.emby_db:
        print(f"\nReading Emby legacy DB: {args.emby_db}")
        rows = open_legacy(args.emby_db)
        print(f"  Found {len(rows)} rows.")
        for row in rows:
            discord_id = str(row.get('discord_username') or row.get('discord_id') or '').strip()
            # In emby.db the jellyfin_username column holds the emby username
            media_username = str(row.get('jellyfin_username') or row.get('emby_username') or '').strip()
            email = str(row.get('email') or '').strip() or None

            if not discord_id:
                continue

            dest.execute(
                "INSERT OR IGNORE INTO clients(discord_id, email) VALUES(?, ?)",
                (discord_id, email)
            )
            if email:
                dest.execute(
                    "UPDATE clients SET email=? WHERE discord_id=? AND email IS NULL",
                    (email, discord_id)
                )

            if media_username:
                dest.execute(
                    "INSERT OR IGNORE INTO server_accounts(discord_id, server_type, server_name, username) VALUES(?, ?, ?, ?)",
                    (discord_id, 'emby', args.emby_name, media_username)
                )
                emby_imported += 1

        dest.commit()

    # ── Summary ──
    cur = dest.cursor()
    cur.execute("SELECT COUNT(*) FROM clients")
    total_clients = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM server_accounts")
    total_sa = cur.fetchone()[0]
    dest.close()

    print(f"\n{'='*50}")
    print(f"Migration complete!")
    print(f"  Jellyfin accounts imported : {jf_imported}")
    print(f"  Emby accounts imported     : {emby_imported}")
    print(f"  Total clients rows         : {total_clients}")
    print(f"  Total server_accounts rows : {total_sa}")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Import legacy Jellyfin/Emby DBs into Membarr V1.4 DB")
    parser.add_argument("--jellyfin-db", default="jellyfin.db", help="Path to legacy jellyfin.db")
    parser.add_argument("--jellyfin-name", default="Jellyfin", help="Server name to assign Jellyfin accounts")
    parser.add_argument("--emby-db", default="emby.db", help="Path to legacy emby.db")
    parser.add_argument("--emby-name", default="Emby", help="Server name to assign Emby accounts")
    parser.add_argument("--output", default="app/config/app.db", help="Target app.db path")
    args = parser.parse_args()
    migrate(args)


if __name__ == "__main__":
    main()

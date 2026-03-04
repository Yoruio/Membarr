import sqlite3

CURRENT_VERSION = 'Membarr V1.4'

table_history = {
    'Invitarr V1.0': [
        (0, 'id', 'INTEGER', 1, None, 1),
        (1, 'discord_username', 'TEXT', 1, None, 0),
        (2, 'email', 'TEXT', 1, None, 0)
    ],
    'Membarr V1.1': [
        (0, 'id', 'INTEGER', 1, None, 1),
        (1, 'discord_username', 'TEXT', 1, None, 0),
        (2, 'email', 'TEXT', 0, None, 0),
        (3, 'jellyfin_username', 'TEXT', 0, None, 0)
    ],
    'Membarr V1.2': [
        (0, 'id', 'INTEGER', 1, None, 1),
        (1, 'discord_id', 'TEXT', 1, None, 0),
        (2, 'email', 'TEXT', 0, None, 0),
        (3, 'jellyfin_username', 'TEXT', 0, None, 0)
    ],
    'Membarr V1.3': [
        (0, 'id', 'INTEGER', 1, None, 1),
        (1, 'discord_id', 'TEXT', 1, None, 0),
        (2, 'email', 'TEXT', 0, None, 0),
        (3, 'jellyfin_username', 'TEXT', 0, None, 0),
        (4, 'emby_username', 'TEXT', 0, None, 0)
    ],
    'Membarr V1.4': [
        (0, 'id', 'INTEGER', 1, None, 1),
        (1, 'discord_id', 'TEXT', 1, None, 0),
        (2, 'email', 'TEXT', 0, None, 0),
    ]
}

def check_table_version(conn, tablename):
    dbcur = conn.cursor()
    dbcur.execute(f"PRAGMA table_info({tablename})")
    table_format = dbcur.fetchall()
    for app_version in table_history:
        if table_history[app_version] == table_format:
            return app_version
    raise ValueError("Could not identify database table version.")

def update_table(conn, tablename):
    version = check_table_version(conn, tablename)
    print('------')
    print(f'DB table version: {version}')
    if version == CURRENT_VERSION:
        print('DB table up to date!')
        print('------')
        return

    # Table NOT up to date — run migrations in order.

    # Invitarr V1.0 → Membarr V1.1: add jellyfin_username column, relax email NOT NULL
    if version == 'Invitarr V1.0':
        print("Upgrading DB table from Invitarr v1.0 to Membarr V1.1")
        conn.execute(
        '''CREATE TABLE "membarr_temp_upgrade_table" (
        "id"	INTEGER NOT NULL UNIQUE,
        "discord_username"	TEXT NOT NULL UNIQUE,
        "email"	TEXT,
        "jellyfin_username" TEXT,
        PRIMARY KEY("id" AUTOINCREMENT)
        );''')
        conn.execute(f'''
        INSERT INTO membarr_temp_upgrade_table(id, discord_username, email)
        SELECT id, discord_username, email
        FROM {tablename};
        ''')
        conn.execute(f'DROP TABLE {tablename};')
        conn.execute(f'ALTER TABLE membarr_temp_upgrade_table RENAME TO {tablename}')
        conn.commit()
        version = 'Membarr V1.1'

    # Membarr V1.1 → Membarr V1.2: rename discord_username → discord_id
    if version == 'Membarr V1.1':
        print("Upgrading DB table from Membarr V1.1 to Membarr V1.2 (renaming discord_username to discord_id)")
        conn.execute(
        '''CREATE TABLE "membarr_temp_upgrade_table" (
        "id"	INTEGER NOT NULL UNIQUE,
        "discord_id"	TEXT NOT NULL UNIQUE,
        "email"	TEXT,
        "jellyfin_username" TEXT,
        PRIMARY KEY("id" AUTOINCREMENT)
        );''')
        conn.execute(f'''
        INSERT INTO membarr_temp_upgrade_table(id, discord_id, email, jellyfin_username)
        SELECT id, discord_username, email, jellyfin_username
        FROM {tablename};
        ''')
        conn.execute(f'DROP TABLE {tablename};')
        conn.execute(f'ALTER TABLE membarr_temp_upgrade_table RENAME TO {tablename}')
        conn.commit()
        version = 'Membarr V1.2'

    # Membarr V1.2 → Membarr V1.3: add emby_username column
    if version == 'Membarr V1.2':
        print("Upgrading DB table from Membarr V1.2 to Membarr V1.3 (adding emby_username column)")
        conn.execute(f"ALTER TABLE {tablename} ADD COLUMN emby_username TEXT")
        conn.commit()
        version = 'Membarr V1.3'

    # Membarr V1.3 → Membarr V1.4: move jellyfin/emby usernames into server_accounts table
    if version == 'Membarr V1.3':
        print("Upgrading DB table from Membarr V1.3 to Membarr V1.4 (migrating jellyfin/emby to server_accounts)")

        # Create server_accounts table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS "server_accounts" (
            "id"          INTEGER PRIMARY KEY AUTOINCREMENT,
            "discord_id"  TEXT NOT NULL,
            "server_type" TEXT NOT NULL,
            "server_name" TEXT NOT NULL,
            "username"    TEXT NOT NULL,
            UNIQUE("discord_id", "server_type", "server_name")
        );''')

        # Migrate existing jellyfin_username entries (default server name "Jellyfin")
        conn.execute('''
        INSERT OR IGNORE INTO server_accounts(discord_id, server_type, server_name, username)
        SELECT discord_id, 'jellyfin', 'Jellyfin', jellyfin_username
        FROM clients
        WHERE jellyfin_username IS NOT NULL AND jellyfin_username != '';
        ''')

        # Migrate existing emby_username entries (default server name "Emby")
        conn.execute('''
        INSERT OR IGNORE INTO server_accounts(discord_id, server_type, server_name, username)
        SELECT discord_id, 'emby', 'Emby', emby_username
        FROM clients
        WHERE emby_username IS NOT NULL AND emby_username != '';
        ''')

        # Rebuild clients table without jellyfin_username and emby_username columns
        conn.execute('''
        CREATE TABLE "membarr_temp_upgrade_table" (
            "id"         INTEGER NOT NULL UNIQUE,
            "discord_id" TEXT NOT NULL UNIQUE,
            "email"      TEXT,
            PRIMARY KEY("id" AUTOINCREMENT)
        );''')
        conn.execute(f'''
        INSERT INTO membarr_temp_upgrade_table(id, discord_id, email)
        SELECT id, discord_id, email
        FROM {tablename};
        ''')
        conn.execute(f'DROP TABLE {tablename};')
        conn.execute(f'ALTER TABLE membarr_temp_upgrade_table RENAME TO {tablename}')
        conn.commit()
        version = 'Membarr V1.4'

    print('------')

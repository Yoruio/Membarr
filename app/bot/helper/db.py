import sqlite3

from app.bot.helper.dbupdater import check_table_version, update_table

DB_URL = 'app/config/app.db'
DB_TABLE = 'clients'

def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print("Connected to db")
    except Exception as e:
        print("error in connecting to db")
    finally:
        if conn:
            return conn

def checkTableExists(dbcon, tablename):
    dbcur = dbcon.cursor()
    dbcur.execute("""SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{0}';""".format(tablename.replace('\'', '\'\'')))
    if dbcur.fetchone()[0] == 1:
        dbcur.close()
        return True
    dbcur.close()
    return False

conn = create_connection(DB_URL)

# Enable WAL mode so the web UI process can read concurrently without blocking
conn.execute("PRAGMA journal_mode=WAL")

# Create clients table for fresh installs (V1.4 schema — no jellyfin/emby columns)
if checkTableExists(conn, DB_TABLE):
    print('Table exists.')
else:
    conn.execute(
    '''CREATE TABLE "clients" (
    "id"         INTEGER NOT NULL UNIQUE,
    "discord_id" TEXT NOT NULL UNIQUE,
    "email"      TEXT,
    PRIMARY KEY("id" AUTOINCREMENT)
    );''')

# Always ensure server_accounts table exists
conn.execute('''
CREATE TABLE IF NOT EXISTS "server_accounts" (
    "id"          INTEGER PRIMARY KEY AUTOINCREMENT,
    "discord_id"  TEXT NOT NULL,
    "server_type" TEXT NOT NULL,
    "server_name" TEXT NOT NULL,
    "username"    TEXT NOT NULL,
    UNIQUE("discord_id", "server_type", "server_name")
);''')
conn.commit()

update_table(conn, DB_TABLE)


# ── Plex (email-based) functions ──────────────────────────────────────────────

def save_user_email(username, email):
    if username and email:
        conn.execute(
            "INSERT OR REPLACE INTO clients(discord_id, email) VALUES(?, ?)",
            (str(username), email)
        )
        conn.commit()
        print("User added to db.")
    else:
        return "Username and email cannot be empty"

def save_user(username):
    if username:
        conn.execute("INSERT OR IGNORE INTO clients (discord_id) VALUES (?)", (str(username),))
        conn.commit()
        print("User added to db.")
    else:
        return "Username cannot be empty"

def get_useremail(username):
    if username:
        try:
            cursor = conn.execute(
                "SELECT email FROM clients WHERE discord_id = ?",
                (str(username),)
            )
            row = cursor.fetchone()
            return row[0] if row and row[0] else "No email found"
        except:
            return "error in fetching from db"
    else:
        return "username cannot be empty"

def remove_email(username):
    """Sets email of discord user to null in database."""
    if username:
        conn.execute("UPDATE clients SET email = NULL WHERE discord_id = ?", (str(username),))
        conn.commit()
        print(f"Email removed from user {username} in database")
        return True
    else:
        print("Username cannot be empty.")
        return False


# ── Generic multi-server account functions ────────────────────────────────────

def save_server_account(discord_id, server_type, server_name, username):
    """Save or update a media server account for a Discord user."""
    if discord_id and server_type and server_name and username:
        # Ensure the user exists in clients
        conn.execute(
            "INSERT OR IGNORE INTO clients(discord_id) VALUES(?)",
            (str(discord_id),)
        )
        conn.execute(
            "INSERT OR REPLACE INTO server_accounts(discord_id, server_type, server_name, username) VALUES(?, ?, ?, ?)",
            (str(discord_id), server_type, server_name, username)
        )
        conn.commit()
        print(f"Server account saved: {discord_id} → {server_type}/{server_name}: {username}")
    else:
        return "All parameters are required"

def get_server_account(discord_id, server_type, server_name):
    """Return the username for a Discord user on a given server, or None."""
    if discord_id and server_type and server_name:
        cursor = conn.execute(
            "SELECT username FROM server_accounts WHERE discord_id=? AND server_type=? AND server_name=?",
            (str(discord_id), server_type, server_name)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    return None

def remove_server_account(discord_id, server_type, server_name):
    """Delete the server_accounts row for a Discord user on a given server."""
    if discord_id and server_type and server_name:
        conn.execute(
            "DELETE FROM server_accounts WHERE discord_id=? AND server_type=? AND server_name=?",
            (str(discord_id), server_type, server_name)
        )
        conn.commit()
        print(f"Server account removed: {discord_id} from {server_type}/{server_name}")
        return True
    return False

def get_all_server_accounts(discord_id):
    """Return all server accounts for a Discord user as list of (server_type, server_name, username)."""
    cursor = conn.execute(
        "SELECT server_type, server_name, username FROM server_accounts WHERE discord_id=?",
        (str(discord_id),)
    )
    return cursor.fetchall()


# ── User management ───────────────────────────────────────────────────────────

def delete_user(username):
    """Delete a user from both clients and server_accounts tables."""
    if username:
        try:
            conn.execute("DELETE FROM clients WHERE discord_id = ?", (str(username),))
            conn.execute("DELETE FROM server_accounts WHERE discord_id = ?", (str(username),))
            conn.commit()
            return True
        except:
            return False
    else:
        return "username cannot be empty"

def read_all():
    """Return all users as list of (id, discord_id, email, server_accounts).
    server_accounts is a list of (server_type, server_name, username) tuples."""
    cur = conn.cursor()
    cur.execute("SELECT id, discord_id, email FROM clients")
    rows = cur.fetchall()
    result = []
    for row in rows:
        accounts = get_all_server_accounts(row[1])
        result.append((row[0], row[1], row[2], accounts))
    return result

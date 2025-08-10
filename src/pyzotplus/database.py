"""SQLite database helpers for Pyzotplus.

This module manages connections and provides simple CRUD helpers for the
main Zotero entities used by :mod:`pyzotplus`.  It relies on the standard
library :mod:`sqlite3` module and uses FTS5 for full-text search.
"""

from __future__ import annotations

from datetime import datetime
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Updated schema version to include sync metadata
SCHEMA_VERSION = 3


def init_db(path: str) -> sqlite3.Connection:
    """Initialise a connection to the SQLite database.

    Parameters
    ----------
    path:
        Filesystem path to the SQLite database file.

    Returns
    -------
    sqlite3.Connection
        An open connection with foreign keys enabled.  If the schema version
        is outdated migrations are applied automatically.
    """

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current < SCHEMA_VERSION:
        migrate(conn, current, SCHEMA_VERSION)
    return conn


def migrate(conn: sqlite3.Connection, current: int, target: int) -> None:
    """Run migrations to bring the schema to *target* version."""

    for version in range(current + 1, target + 1):
        func = MIGRATIONS.get(version)
        if func is None:
            raise RuntimeError(f"No migration available for version {version}")
        func(conn)
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()


def _create_schema_v1(conn: sqlite3.Connection) -> None:
    """Initial database schema."""

    conn.executescript(
        """
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            key TEXT UNIQUE,
            title TEXT,
            collection_id INTEGER,
            data TEXT,
            FOREIGN KEY(collection_id) REFERENCES collections(id) ON DELETE SET NULL
        );

        CREATE TABLE collections (
            id INTEGER PRIMARY KEY,
            key TEXT UNIQUE,
            name TEXT
        );

        CREATE TABLE tags (
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            tag TEXT
        );

        CREATE TABLE attachments (
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            filename TEXT,
            path TEXT
        );

        CREATE TABLE notes (
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            content TEXT
        );

        CREATE VIRTUAL TABLE fulltext USING fts5(
            item_id UNINDEXED,
            content
        );
        """
    )


def _upgrade_schema_v2(conn: sqlite3.Connection) -> None:
    """Add sync metadata columns and tables."""

    conn.execute("ALTER TABLE items ADD COLUMN version INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE items ADD COLUMN synced_at TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )


def _upgrade_schema_v3(conn: sqlite3.Connection) -> None:
    """Add table for reusable note templates."""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS note_templates (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            content TEXT
        );
        """
    )


MIGRATIONS = {1: _create_schema_v1, 2: _upgrade_schema_v2, 3: _upgrade_schema_v3}


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

# Items ---------------------------------------------------------------------

def add_item(
    conn: sqlite3.Connection,
    key: str,
    title: str,
    data: str,
    collection_id: Optional[int] = None,
    version: int = 0,
    synced_at: Optional[str] = None,
) -> int:
    """Insert a new item and return its row id."""

    cur = conn.execute(
        """
        INSERT INTO items(key, title, data, collection_id, version, synced_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (key, title, data, collection_id, version, synced_at),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_item(conn: sqlite3.Connection, item_id: int) -> Optional[sqlite3.Row]:
    """Fetch a single item by *item_id*."""

    return conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()


def update_item(conn: sqlite3.Connection, item_id: int, **fields: Any) -> None:
    """Update fields on an item."""

    if not fields:
        return
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [item_id]
    conn.execute(f"UPDATE items SET {columns} WHERE id = ?", values)
    conn.commit()


def delete_item(conn: sqlite3.Connection, item_id: int) -> None:
    """Remove an item and all dependent records."""

    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.execute("DELETE FROM fulltext WHERE item_id = ?", (item_id,))
    conn.commit()


# Collections ---------------------------------------------------------------

def add_collection(conn: sqlite3.Connection, key: str, name: str) -> int:
    cur = conn.execute("INSERT INTO collections(key, name) VALUES (?, ?)", (key, name))
    conn.commit()
    return int(cur.lastrowid)


def get_collection(
    conn: sqlite3.Connection, collection_id: int
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM collections WHERE id = ?", (collection_id,)
    ).fetchone()


def update_collection(conn: sqlite3.Connection, collection_id: int, **fields: Any) -> None:
    if not fields:
        return
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [collection_id]
    conn.execute(f"UPDATE collections SET {columns} WHERE id = ?", values)
    conn.commit()


def delete_collection(conn: sqlite3.Connection, collection_id: int) -> None:
    conn.execute("UPDATE items SET collection_id = NULL WHERE collection_id = ?", (collection_id,))
    conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
    conn.commit()


# Tags ---------------------------------------------------------------------

def add_tag(conn: sqlite3.Connection, item_id: int, tag: str) -> int:
    cur = conn.execute(
        "INSERT INTO tags(item_id, tag) VALUES (?, ?)",
        (item_id, tag),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_tags(conn: sqlite3.Connection, item_id: Optional[int] = None) -> List[sqlite3.Row]:
    if item_id is None:
        cur = conn.execute("SELECT * FROM tags")
    else:
        cur = conn.execute("SELECT * FROM tags WHERE item_id = ?", (item_id,))
    return cur.fetchall()


def delete_tag(conn: sqlite3.Connection, tag_id: int) -> None:
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()


# Attachments ---------------------------------------------------------------

def add_attachment(
    conn: sqlite3.Connection, item_id: int, filename: str, path: str
) -> int:
    cur = conn.execute(
        "INSERT INTO attachments(item_id, filename, path) VALUES (?, ?, ?)",
        (item_id, filename, path),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_attachment(
    conn: sqlite3.Connection, attachment_id: int
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM attachments WHERE id = ?", (attachment_id,)
    ).fetchone()


def delete_attachment(conn: sqlite3.Connection, attachment_id: int) -> None:
    conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
    conn.commit()


# Notes --------------------------------------------------------------------

def add_note(conn: sqlite3.Connection, item_id: int, content: str) -> int:
    cur = conn.execute(
        "INSERT INTO notes(item_id, content) VALUES (?, ?)",
        (item_id, content),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_note(conn: sqlite3.Connection, note_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()


def update_note(conn: sqlite3.Connection, note_id: int, content: str) -> None:
    conn.execute("UPDATE notes SET content = ? WHERE id = ?", (content, note_id))
    conn.commit()


def delete_note(conn: sqlite3.Connection, note_id: int) -> None:
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()


# Note templates -----------------------------------------------------------

def add_note_template(conn: sqlite3.Connection, name: str, content: str) -> int:
    cur = conn.execute(
        "INSERT INTO note_templates(name, content) VALUES (?, ?)",
        (name, content),
    )
    conn.commit()
    return int(cur.lastrowid)


def get_note_template(conn: sqlite3.Connection, name: str) -> Optional[str]:
    row = conn.execute(
        "SELECT content FROM note_templates WHERE name = ?",
        (name,),
    ).fetchone()
    return row["content"] if row else None


def update_note_template(conn: sqlite3.Connection, name: str, content: str) -> None:
    conn.execute(
        "UPDATE note_templates SET content = ? WHERE name = ?",
        (content, name),
    )
    conn.commit()


def delete_note_template(conn: sqlite3.Connection, name: str) -> None:
    conn.execute("DELETE FROM note_templates WHERE name = ?", (name,))
    conn.commit()


# Full-text search ---------------------------------------------------------

def add_fulltext(conn: sqlite3.Connection, item_id: int, content: str) -> None:
    conn.execute("INSERT INTO fulltext(rowid, item_id, content) VALUES (NULL, ?, ?)", (item_id, content))
    conn.commit()


def search_fulltext(conn: sqlite3.Connection, query: str) -> List[sqlite3.Row]:
    cur = conn.execute("SELECT item_id, content FROM fulltext WHERE fulltext MATCH ?", (query,))
    return cur.fetchall()


def delete_fulltext(conn: sqlite3.Connection, item_id: int) -> None:
    conn.execute("DELETE FROM fulltext WHERE item_id = ?", (item_id,))
    conn.commit()


# Sync metadata -------------------------------------------------------------

def get_last_sync_version(conn: sqlite3.Connection) -> int:
    """Return the last synced library version."""

    row = conn.execute(
        "SELECT value FROM sync_meta WHERE key = 'library_version'"
    ).fetchone()
    return int(row["value"]) if row else 0


def update_last_sync(conn: sqlite3.Connection, version: int) -> None:
    """Update sync metadata with *version* and current timestamp."""

    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO sync_meta(key, value) VALUES ('library_version', ?)",
        (str(version),),
    )
    conn.execute(
        "INSERT OR REPLACE INTO sync_meta(key, value) VALUES ('last_sync', ?)",
        (now,),
    )
    conn.commit()


__all__ = [
    "SCHEMA_VERSION",
    "init_db",
    "migrate",
    "add_item",
    "get_item",
    "update_item",
    "delete_item",
    "add_collection",
    "get_collection",
    "update_collection",
    "delete_collection",
    "add_tag",
    "list_tags",
    "delete_tag",
    "add_attachment",
    "get_attachment",
    "delete_attachment",
    "add_note",
    "get_note",
    "update_note",
    "delete_note",
    "add_note_template",
    "get_note_template",
    "update_note_template",
    "delete_note_template",
    "add_fulltext",
    "search_fulltext",
    "delete_fulltext",
    "get_last_sync_version",
    "update_last_sync",
]

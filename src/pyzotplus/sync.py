"""Synchronisation helpers for Pyzotplus.

This module provides simple :func:`pull_changes` and :func:`push_changes`
functions which keep a local SQLite database in sync with a remote Zotero
library.  The implementation is intentionally lightweight and relies on
the existing :class:`~pyzotplus.zotero.Zotero` client for all network
communication.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Dict, Optional

from . import database
from .zotero import Zotero


def pull_changes(conn: sqlite3.Connection, zot: Zotero) -> None:
    """Pull remote changes into the local database.

    The function retrieves remote item versions since the last sync and
    compares them with the versions stored locally.  Items missing locally
    or with older versions are fetched from the server and written to the
    database.  Conflicts are resolved in favour of the newest item version.
    """

    last_version = database.get_last_sync_version(conn)
    remote_versions: Dict[str, int] = zot.item_versions(since=last_version)

    for key, version in remote_versions.items():
        item = zot.item(key)
        row = conn.execute(
            "SELECT id, version FROM items WHERE key = ?", (key,)
        ).fetchone()
        synced_at = datetime.utcnow().isoformat()
        data_json = json.dumps(item)
        title = item.get("data", {}).get("title", "")
        if row is None:
            database.add_item(
                conn, key, title, data_json, version=version, synced_at=synced_at
            )
        elif row["version"] < version:
            database.update_item(
                conn,
                row["id"],
                title=title,
                data=data_json,
                version=version,
                synced_at=synced_at,
            )

    new_version = zot.last_modified_version()
    database.update_last_sync(conn, new_version)


def push_changes(conn: sqlite3.Connection, zot: Zotero) -> None:
    """Push local changes to the remote Zotero library.

    Local items with versions greater than those on the server are sent to
    the remote library.  If the server reports a newer version, the local
    copy is updated instead.  In both cases the local sync metadata is
    refreshed.
    """

    remote_versions: Dict[str, int] = zot.item_versions()

    for row in conn.execute("SELECT id, key, version, data FROM items"):
        key = row["key"]
        local_version = row["version"] or 0
        remote_version = remote_versions.get(key, 0)
        if local_version > remote_version:
            item = json.loads(row["data"])
            item["key"] = key
            item["version"] = remote_version
            zot.update_item(item, last_modified=remote_version)
            updated = zot.item(key)
            database.update_item(
                conn,
                row["id"],
                data=json.dumps(updated),
                version=updated["version"],
                synced_at=datetime.utcnow().isoformat(),
            )
        elif remote_version > local_version:
            item = zot.item(key)
            database.update_item(
                conn,
                row["id"],
                data=json.dumps(item),
                version=item["version"],
                synced_at=datetime.utcnow().isoformat(),
            )

    new_version = zot.last_modified_version()
    database.update_last_sync(conn, new_version)


def write_note(
    conn: sqlite3.Connection,
    zot: Zotero,
    parent_key: str,
    template_name: str,
    **data: str,
) -> Optional[str]:
    """Create a note from a stored template and sync it.

    The note content is generated from a named template stored in the
    database.  The resulting note is uploaded to Zotero and stored locally.

    Parameters
    ----------
    conn:
        Open SQLite connection.
    zot:
        :class:`Zotero` client instance.
    parent_key:
        Zotero key of the item the note should be attached to.
    template_name:
        Name of the template stored in the database.
    **data:
        Values used to fill the template placeholders.

    Returns
    -------
    Optional[str]
        The newly created note key, if creation was successful.
    """

    content_tpl = database.get_note_template(conn, template_name)
    note = zot.note_template()
    template = content_tpl or note["note"]
    note["note"] = template.format(**data)
    resp = zot.create_items([note], parentid=parent_key)
    row = conn.execute(
        "SELECT id FROM items WHERE key = ?",
        (parent_key,),
    ).fetchone()
    if row:
        database.add_note(conn, row["id"], note["note"])
    return next(iter(resp.get("success", {}).values()), None)


__all__ = ["pull_changes", "push_changes", "write_note"]


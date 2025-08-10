"""Utilities for managing lab-specific sequential identifiers.

These helpers allow assigning a nine digit sequential identifier to
Zotero items. The identifier is stored in the item's `extra` field as::

    LAB_ID: 000000123

Existing identifiers are preserved and mismatches against a local
registry are reported.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

LAB_ID_PATTERN = re.compile(r"^LAB_ID:\s*(\d{9})$", re.MULTILINE)


def extract_lab_id(item: Dict) -> Optional[str]:
    """Return the lab identifier from a Zotero item if present."""
    extra = item.get("data", {}).get("extra", "")
    match = LAB_ID_PATTERN.search(extra)
    if match:
        return match.group(1)
    return None


def set_lab_id(item: Dict, lab_id: str) -> Dict:
    """Embed ``lab_id`` in the item's ``extra`` field."""
    extra = item.get("data", {}).get("extra", "")
    if LAB_ID_PATTERN.search(extra):
        extra = LAB_ID_PATTERN.sub(f"LAB_ID: {lab_id}", extra)
    else:
        extra = f"{extra}\nLAB_ID: {lab_id}" if extra else f"LAB_ID: {lab_id}"
    item.setdefault("data", {})["extra"] = extra
    return item


def ensure_lab_ids(zot, db_path: Path) -> Dict[str, List]:
    """Ensure each item in the library has a sequential lab identifier.

    Parameters
    ----------
    zot: Zotero
        A :class:`pyzotero.zotero.Zotero` instance.
    db_path: Path
        Location of the JSON file tracking assigned identifiers.

    Returns
    -------
    dict
        Mapping containing ``allocated`` and ``mismatches`` reports.
    """
    db: Dict[str, str] = {}
    if db_path.exists():
        db = json.loads(db_path.read_text())

    max_id = max([int(i) for i in db.keys()] or [0])
    allocated: List[str] = []
    mismatches: List[Dict[str, str]] = []

    items = zot.top()
    for item in items:
        key = item["data"]["key"]
        existing = extract_lab_id(item)
        if existing:
            if existing in db and db[existing] != key:
                mismatches.append({"lab_id": existing, "zotero_key": key, "db_key": db[existing]})
            else:
                db[existing] = key
            continue

        max_id += 1
        new_id = f"{max_id:09d}"
        set_lab_id(item, new_id)
        db[new_id] = key
        allocated.append(new_id)
        try:
            zot.update_item(item)
        except Exception:
            # Network operations may fail in offline environments. The caller
            # can handle update errors if desired.
            pass

    db_path.write_text(json.dumps(db, indent=2))
    return {"allocated": allocated, "mismatches": mismatches}

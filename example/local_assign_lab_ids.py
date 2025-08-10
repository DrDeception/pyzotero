"""Example script for assigning sequential lab identifiers to Zotero items.

This demonstrates how to use :mod:`pyzotero.lab_id` to ensure every item in a
local Zotero database has a nine digit identifier stored in the ``extra`` field.

The script expects a ``local_ids.json`` file to track assigned identifiers and
uses read/write access to the local Zotero database.
"""

from pathlib import Path

from pyzotero import zotero
from pyzotero.lab_id import ensure_lab_ids


if __name__ == "__main__":
    LIB_ID = "your_library_id"
    API_KEY = "your_api_key"

    zot = zotero.Zotero(LIB_ID, "user", API_KEY, local=True)
    report = ensure_lab_ids(zot, Path("local_ids.json"))
    print("Allocated:", report["allocated"])
    print("Mismatches:", report["mismatches"])

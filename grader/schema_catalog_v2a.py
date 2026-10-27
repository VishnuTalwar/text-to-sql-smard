"""
Catalog v2a: the schema catalog with ONLY the Kernenergie quirk reworded.

This is ablation row v2a (on top of the decline setup). It is built from
schema_catalog.CATALOG by replacing that one note, so every other table,
column, value list and quirk is identical by construction. schema_catalog.py
is not modified, which keeps all earlier setups reproducible.
"""

import copy

from schema_catalog import CATALOG as _BASE_CATALOG

OLD_KERNENERGIE_NOTE = (
    "Kernenergie is NULL after 2024-01-30, not zero. "
    "Use NULLS LAST on any ORDER BY ... DESC over this column, or "
    "Kernenergie sorts to the top incorrectly."
)

NEW_KERNENERGIE_NOTE = (
    "Kernenergie has no data after 2024-01-30: its mwh is NULL from then on, "
    "so any SUM, AVG or MAX of Kernenergie over a later period is also NULL. "
    "In PostgreSQL, NULL sorts first in ORDER BY ... DESC, so when ranking energy sources "
    "by a total or average, write ORDER BY <total> DESC NULLS LAST."
)

CATALOG: dict[str, dict] = copy.deepcopy(_BASE_CATALOG)

_quirks = CATALOG["erzeugung"]["quirks"]
if _quirks.count(OLD_KERNENERGIE_NOTE) != 1:
    raise RuntimeError(
        "schema_catalog.py no longer contains the expected Kernenergie note exactly once; "
        "update OLD_KERNENERGIE_NOTE here."
    )
_quirks[_quirks.index(OLD_KERNENERGIE_NOTE)] = NEW_KERNENERGIE_NOTE

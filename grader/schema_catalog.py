"""
Static schema catalog for the three SMARD tables.

Entries contain: table purpose, columns (name, type, example values),
distinct categorical values, and data quirks.

The quirks text is taken verbatim from PROJECT.md sections 3 and 4 —
do not paraphrase or summarise. Precision matters: the Kernenergie NULL
and the Pumpspeicher dual-meaning failures in the baseline log are exactly
the traps these notes are meant to prevent.
"""

# Each top-level key is a table name.
# Each entry has:
#   purpose   – one sentence describing what the table holds
#   columns   – list of {name, type, examples}
#   values    – dict of {column_name: [categorical values]}   (only for text columns with a closed vocabulary)
#   quirks    – list of plain-text notes, scoped to this table (or cross-table)
#
# The catalog is a plain Python dict so it can be imported directly without
# any file I/O — no YAML loader, no JSON, nothing to go wrong at startup.

CATALOG: dict[str, dict] = {
    "erzeugung": {
        "purpose": (
            "Realised electricity generation: one row per 15-minute interval per energy source, "
            "in MWh (energy generated in that quarter-hour)."
        ),
        "columns": [
            {
                "name": "zeitpunkt",
                "type": "timestamp",
                "examples": ["2023-06-01 00:00", "2024-12-12 13:00", "2026-06-01 23:45"],
            },
            {
                "name": "energietraeger",
                "type": "text",
                "examples": ["Wind Onshore", "Photovoltaik", "Braunkohle"],
            },
            {
                "name": "mwh",
                "type": "numeric (nullable)",
                "examples": ["13248.60", "0.25", "NULL"],
            },
        ],
        "values": {
            "energietraeger": [
                "Biomasse",
                "Wasserkraft",
                "Wind Offshore",
                "Wind Onshore",
                "Photovoltaik",
                "Sonstige Erneuerbare",
                "Kernenergie",
                "Braunkohle",
                "Steinkohle",
                "Erdgas",
                "Pumpspeicher",
                "Sonstige Konventionelle",
            ]
        },
        "quirks": [
            (
                "Kernenergie is NULL after 2024-01-30, not zero. "
                "Use NULLS LAST on any ORDER BY ... DESC over this column, or "
                "Kernenergie sorts to the top incorrectly."
            ),
            (
                "Values are MWh per 15-minute interval. Report results in MWh as "
                "stored. Only multiply by 4 if the question explicitly asks for MW "
                "or power."
            ),
            (
                "Pumpspeicher means opposite things in the two tables — "
                "generation (releasing water) in erzeugung, "
                "consumption (pumping water up) in verbrauch. Do not conflate."
            ),
            (
                "zeitpunkt has 12 duplicate values across 3 autumn DST changeovers — "
                "be aware when counting distinct timestamps."
            ),
        ],
    },

    "verbrauch": {
        "purpose": (
            "Realised electricity consumption: one row per 15-minute interval per metric, "
            "in MWh (energy consumed in that quarter-hour)."
        ),
        "columns": [
            {
                "name": "zeitpunkt",
                "type": "timestamp",
                "examples": ["2023-06-01 00:00", "2025-01-15 08:15", "2026-03-31 23:45"],
            },
            {
                "name": "metrik",
                "type": "text",
                "examples": ["grid load", "Residual load", "Hydro pumped storage"],
            },
            {
                "name": "mwh",
                "type": "numeric (nullable)",
                "examples": ["13248.60", "9812.25", "NULL"],
            },
        ],
        "values": {
            # Note: verbrauch metrik values are English — unlike erzeugung and preise which are German.
            "metrik": [
                "grid load",
                "Grid load incl. hydro pumped storage",
                "Hydro pumped storage",
                "Residual load",
            ]
        },
        "quirks": [
            (
                "Pumpspeicher means opposite things in the two tables — "
                "generation (releasing water) in erzeugung, "
                "consumption (pumping water up) in verbrauch. Do not conflate."
            ),
            (
                "Values are MWh per 15-minute interval. Report results in MWh as "
                "stored. Only multiply by 4 if the question explicitly asks for MW "
                "or power."
            ),
            (
                "The metrik values are in English (e.g. 'grid load', 'Residual load'), "
                "unlike erzeugung and preise which use German labels — match exactly."
            ),
            (
                "zeitpunkt has 12 duplicate values across 3 autumn DST changeovers — "
                "be aware when counting distinct timestamps."
            ),
        ],
    },

    "preise": {
        "purpose": (
            "Wholesale electricity prices: one row per 15-minute interval per price zone, "
            "in EUR/MWh."
        ),
        "columns": [
            {
                "name": "zeitpunkt",
                "type": "timestamp",
                "examples": ["2023-06-01 00:00", "2024-12-12 13:00", "2025-10-26 02:00"],
            },
            {
                "name": "preiszone",
                "type": "text",
                "examples": ["Deutschland/Luxemburg", "Frankreich", "Österreich"],
            },
            {
                "name": "preis_eur_mwh",
                "type": "numeric (nullable)",
                "examples": ["936.28", "45.12", "NULL"],
            },
        ],
        "values": {
            "preiszone": [
                "Deutschland/Luxemburg",
                "∅ Anrainer DE/LU",
                "Belgien",
                "Dänemark 1",
                "Dänemark 2",
                "Frankreich",
                "Niederlande",
                "Norwegen 2",
                "Österreich",
                "Polen",
                "Schweden 4",
                "Schweiz",
                "Tschechien",
                "DE/AT/LU",
                "Italien (Nord)",
                "Slowenien",
                "Ungarn",
            ]
        },
        "quirks": [
            (
                "DE/AT/LU is a valid preiszone value but is entirely "
                "empty (all NULL) for the whole dataset — exclude it from any "
                "aggregate with HAVING COUNT(preis_eur_mwh) > 0, or it will "
                "appear as a false extreme value."
            ),
            (
                "zeitpunkt has 12 duplicate values across 3 autumn DST changeovers — "
                "be aware when counting distinct timestamps."
            ),
        ],
    },
}

"""
Naive baseline prompt: raw schema + question, nothing else.

Deliberately excludes every quirk in PROJECT.md section 4 (Kernenergie
NULL-vs-zero, Pumpspeicher's dual meaning across tables, DST duplicate
timestamps, etc.) — this baseline measures what the model can do with only
the schema, no domain knowledge. That gap is exactly what the later
"+ schema linking" ablation row is meant to close. See PROJECT.md section 11.
"""

SCHEMA = """\
Table: erzeugung
  zeitpunkt      timestamp
  energietraeger text
  mwh            numeric

Table: verbrauch
  zeitpunkt timestamp
  metrik    text
  mwh       numeric

Table: preise
  zeitpunkt      timestamp
  preiszone      text
  preis_eur_mwh  numeric
"""

ENERGIETRAEGER_VALUES = [
    "Biomasse", "Wasserkraft", "Wind Offshore", "Wind Onshore", "Photovoltaik",
    "Sonstige Erneuerbare", "Kernenergie", "Braunkohle", "Steinkohle", "Erdgas",
    "Pumpspeicher", "Sonstige Konventionelle",
]

METRIK_VALUES = [
    "grid load", "Grid load incl. hydro pumped storage",
    "Hydro pumped storage", "Residual load",
]

PREISZONE_VALUES = [
    "Deutschland/Luxemburg", "∅ Anrainer DE/LU", "Belgien", "Dänemark 1", "Dänemark 2",
    "Frankreich", "Niederlande", "Norwegen 2", "Österreich", "Polen", "Schweden 4",
    "Schweiz", "Tschechien", "DE/AT/LU", "Italien (Nord)", "Slowenien", "Ungarn",
]


def build_prompt(question: str) -> str:
    return (
        f"{SCHEMA}\n"
        f"erzeugung.energietraeger values: {', '.join(ENERGIETRAEGER_VALUES)}\n"
        f"verbrauch.metrik values: {', '.join(METRIK_VALUES)}\n"
        f"preise.preiszone values: {', '.join(PREISZONE_VALUES)}\n"
        f"\n"
        f"Question: {question}\n"
        f"\n"
        f"Return exactly one PostgreSQL SELECT statement that answers the question. "
        f"Return only the SQL — no markdown code fences, no explanation, no other text."
    )

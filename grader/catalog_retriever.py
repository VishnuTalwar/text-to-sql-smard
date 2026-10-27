"""
Keyword-based table retriever for schema linking.

get_relevant_tables(question) maps a natural-language question to the
subset of tables whose schema should be injected into the prompt.

Design decisions:
- Simple keyword matching, no embeddings. The goal of this ablation row
  is to measure whether schema content (the catalog itself) helps, not
  whether a retrieval model helps. Using simple keyword matching keeps
  retrieval quality high enough that a later ablation row can swap in
  semantic retrieval and isolate *that* effect cleanly.
- When ambiguous (no clear match, or multiple topics), return all three
  tables. Returning too few tables is a hard failure (the model has no
  schema for the table it needs). Returning too many is only noise.
- All matches are logged per question so the failure analysis can
  distinguish retrieval mistakes from catalog-content mistakes.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword lists — one set per table.
#
# Two principles:
# 1. Cast wide for German and English synonyms; the model's questions may
#    be in either language and may use lay terms, not schema literals.
# 2. Energieträger names all point to erzeugung. The metrik names in verbrauch
#    are English — include both forms. preise keywords are price / €-centric.
# ---------------------------------------------------------------------------

_ERZEUGUNG_KEYWORDS: list[str] = [
    # Table / concept names
    "erzeugung", "generation", "production", "erzeugt", "erzeugen",
    "output", "produced", "generated",
    # Energy sources (energietraeger values) — all 12
    "biomasse", "biomass",
    "wasserkraft", "hydro",               # NB: different from pumpspeicher
    "wind offshore", "wind onshore", "wind",
    "photovoltaik", "solar", "sonne", "sonnenstrom",
    "sonstige erneuerbare", "erneuerbar", "renewable",
    "kernenergie", "nuclear", "atom",
    "braunkohle", "lignite",
    "steinkohle", "coal", "kohle", "kohlestrom",
    "erdgas", "gas",
    "pumpspeicher",                        # present in both tables; included in both
    "sonstige konventionelle",
    # General generation-side terms
    "energietraeger", "energietr",
    "erzeugungsleistung", "kraftwerk",
]

_VERBRAUCH_KEYWORDS: list[str] = [
    # Table / concept names
    "verbrauch", "consumption", "consumed", "verbraucht",
    "netzlast", "stromnetz",
    # metrik column values (English, matching the source data)
    "grid load", "netzlast",
    "residual load", "residuallast",
    "hydro pumped storage",               # the verbrauch-side pumped storage metric
    "pumpspeicher",                        # present in both tables; included in both
    # Lay terms that map to consumption, not generation
    "stromverbrauch", "lastgang", "load",
    "demand",
]

_PREISE_KEYWORDS: list[str] = [
    # Table / concept names
    "preise", "preis", "price", "prices",
    "grosshandelspreis", "großhandelspreis", "wholesale",
    "eur", "euro", "eur/mwh",
    # preiszone values / synonyms
    "preiszone", "zone", "markt",
    "deutschland", "luxemburg", "belgien",
    "frankreich", "niederlande", "osterreich", "österreich",
    "schweden", "norwegen", "schweiz", "tschechien",
    "de/at/lu", "de/lu",
    "marktpreis", "spotpreis", "day-ahead", "intraday",
    "teuerste", "günstigste", "cheapest", "most expensive",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Lower-case and collapse whitespace so matching is whitespace-agnostic."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _matches_any(text_lower: str, keywords: list[str]) -> bool:
    # Match at a word start only (so "eur" does not hit "europe"/"neuer" mid-word,
    # "atom" does not hit "automatic"); suffixes are allowed for German
    # inflections/compounds ("Windkraft", "Preise").
    return any(re.search(r"(?<!\w)" + re.escape(kw), text_lower) for kw in keywords)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

ALL_TABLES: list[str] = ["erzeugung", "verbrauch", "preise"]


def get_relevant_tables(question: str) -> list[str]:
    """Return the list of table names relevant to *question*.

    Rules:
    - Score each table by whether any of its keywords appear in the question.
    - If exactly one table matches, return just that table.
    - If zero or multiple tables match, return all three (safe fallback).
    - Always logs the result for post-run retrieval analysis.
    """
    q = _normalise(question)

    hits = {
        "erzeugung": _matches_any(q, _ERZEUGUNG_KEYWORDS),
        "verbrauch":  _matches_any(q, _VERBRAUCH_KEYWORDS),
        "preise":     _matches_any(q, _PREISE_KEYWORDS),
    }

    matched = [table for table, hit in hits.items() if hit]

    if len(matched) == 1:
        selected = matched
        reason = f"keyword match → {matched[0]}"
    else:
        # Zero matches: no signal → show everything.
        # Multiple matches: ambiguous → show everything.
        selected = ALL_TABLES
        if matched:
            reason = f"multiple matches ({', '.join(matched)}) → all tables"
        else:
            reason = "no keyword match → all tables"

    logger.info("[retriever] %r → %s (%s)", question[:80], selected, reason)
    return selected

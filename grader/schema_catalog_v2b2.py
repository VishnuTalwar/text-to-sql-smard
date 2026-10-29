"""
Catalog v2b2: catalog v2b with ONE sentence changed.

This is ablation row v2b2 (on top of v2b, not v2c). In the preise "Value meanings",
the last sentence of the "∅ Anrainer DE/LU" entry changes:
  old: "Leave it out when ranking or comparing zones."
  new: "Leave it out when ranking or comparing countries."

It is built from schema_catalog_v2b.CATALOG by swapping that sentence, so everything
else is identical by construction. No existing file is modified. The prompt is rendered
by the existing prompt_template_v2b (no date line); run_v2b2.py points it at this catalog.
"""

import copy

from schema_catalog_v2b import CATALOG as _BASE_CATALOG

OLD_SENTENCE = "Leave it out when ranking or comparing zones."
NEW_SENTENCE = "Leave it out when ranking or comparing countries."

CATALOG: dict[str, dict] = copy.deepcopy(_BASE_CATALOG)

_meanings = CATALOG["preise"]["value_meanings"]["preiszone"]
_hits = [i for i, m in enumerate(_meanings) if m.startswith("∅ Anrainer DE/LU:") and m.endswith(OLD_SENTENCE)]
if len(_hits) != 1:
    raise RuntimeError(
        "schema_catalog_v2b no longer has the expected ∅ Anrainer entry ending in the old sentence; "
        "update OLD_SENTENCE here."
    )
_meanings[_hits[0]] = _meanings[_hits[0]][: -len(OLD_SENTENCE)] + NEW_SENTENCE

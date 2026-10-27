"""
Loads gold_set_smard.yaml into typed Question objects.

Per gold_set_smard.yaml's own grading rules (see the header comment block in
that file), every question already carries an explicit `reihenfolge_relevant`
and `toleranz` — the six ROUND()-using questions (t2_07, t3_02, t3_06, t3_07,
t3_10, t3_12) already have their tolerance loosened to 1e-3 in the file
itself. So the defaults below are a fallback for a question that omits a
field (e.g. one added later), not something that's expected to fire on the
current 84-item set — the per-item value in the YAML always wins.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_SET_PATH = PROJECT_ROOT / "gold_set_smard.yaml"

DEFAULT_REIHENFOLGE_RELEVANT = False
DEFAULT_TOLERANZ = 0.005  # relative; only used if a question omits toleranz entirely


@dataclass
class Question:
    id: str
    tier: int
    frage: str
    gold_sql: Optional[str]
    gold_zeilen: Optional[int]
    reihenfolge_relevant: bool
    toleranz: float
    gold_antwort: Optional[str] = None
    hinweis: Optional[str] = None
    fragil: bool = False
    fragil_grund: Optional[str] = None
    beantwortbar: bool = True
    erwartetes_verhalten: Optional[str] = None
    beleg_sql: Optional[str] = None
    beleg_ergebnis: Optional[str] = None

    @property
    def is_tier0(self) -> bool:
        """Tier 0 = unanswerable; identified by the absence of gold_sql, not by tier number alone."""
        return self.gold_sql is None


def load_questions(path: Path = GOLD_SET_PATH) -> list[Question]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    standard = data.get("standard", {})
    standard_reihenfolge = standard.get("reihenfolge_relevant", DEFAULT_REIHENFOLGE_RELEVANT)
    standard_toleranz = standard.get("toleranz", DEFAULT_TOLERANZ)

    questions = []
    for item in data["fragen"]:
        questions.append(
            Question(
                id=item["id"],
                tier=item["tier"],
                frage=item["frage"],
                gold_sql=item.get("gold_sql"),
                gold_zeilen=item.get("gold_zeilen"),
                reihenfolge_relevant=item.get("reihenfolge_relevant", standard_reihenfolge),
                toleranz=item.get("toleranz", standard_toleranz),
                gold_antwort=item.get("gold_antwort"),
                hinweis=item.get("hinweis"),
                fragil=item.get("fragil", False),
                fragil_grund=item.get("fragil_grund"),
                beantwortbar=item.get("beantwortbar", True),
                erwartetes_verhalten=item.get("erwartetes_verhalten"),
                beleg_sql=item.get("beleg_sql"),
                beleg_ergebnis=item.get("beleg_ergebnis"),
            )
        )
    return questions

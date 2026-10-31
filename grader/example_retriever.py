"""
Retrieval of few-shot examples for row ex-b.

The pool is the items of example_bank.yaml that have gold_sql (tier 0 is skipped). The
"frage" of every pool item and the incoming question are embedded with
EMBEDDING_MODEL; retrieve() returns the K most similar pool items by cosine similarity,
ordered so that the most similar one comes LAST (closest to the real question).

Embeddings are cached in cache/embeddings_<model>.json, keyed by the SHA-256 of the
exact text, so a text is embedded once and later runs are reproducible and need no API
call. Ties in similarity are broken by example id.
"""

import hashlib
import json
import math
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

EMBEDDING_MODEL = "text-embedding-3-small"
EXAMPLE_BANK = PROJECT_ROOT / "example_bank.yaml"
CACHE_PATH = Path(__file__).resolve().parent / "cache" / f"embeddings_{EMBEDDING_MODEL}.json"
K = 3

_cache: dict[str, list[float]] | None = None
_pool: list[dict] | None = None
_client: OpenAI | None = None


def _key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_cache() -> dict[str, list[float]]:
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.is_file() else {}
    return _cache


def _embed(texts: list[str]) -> list[list[float]]:
    """Embeddings for texts, in order; only texts missing from the cache are sent to the API."""
    global _client
    cache = _load_cache()
    missing = list(dict.fromkeys(t for t in texts if _key(t) not in cache))
    if missing:
        _client = _client or OpenAI()
        response = _client.embeddings.create(model=EMBEDDING_MODEL, input=missing)
        for text, item in zip(missing, response.data):
            cache[_key(text)] = item.embedding
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
    return [cache[_key(t)] for t in texts]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def load_pool() -> list[dict]:
    """Bank items with gold_sql, each with its embedding under "embedding"."""
    global _pool
    if _pool is None:
        with open(EXAMPLE_BANK, "r", encoding="utf-8") as f:
            items = [it for it in yaml.safe_load(f)["fragen"] if it.get("gold_sql")]
        vectors = _embed([it["frage"] for it in items])
        _pool = [{**it, "embedding": v} for it, v in zip(items, vectors)]
    return _pool


def retrieve(question: str, k: int = K) -> list[tuple[dict, float]]:
    """The k most similar pool items as (item, cosine similarity), most similar LAST."""
    pool = load_pool()
    (q_vec,) = _embed([question])
    scored = sorted(((it, _cosine(q_vec, it["embedding"])) for it in pool),
                    key=lambda p: (-p[1], p[0]["id"]))
    return scored[:k][::-1]

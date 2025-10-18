"""Text utilities used across the CLI."""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Set

KEYWORDS = {"apr", "fees", "foreign transaction", "transaction", "issuer"}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return value.lower() or "artifact"


def detect_keywords(text: str, keywords: Iterable[str] | None = None) -> Set[str]:
    keywords = set(keyword.lower() for keyword in (keywords or KEYWORDS))
    text_lower = text.lower()
    return {keyword for keyword in keywords if keyword in text_lower}

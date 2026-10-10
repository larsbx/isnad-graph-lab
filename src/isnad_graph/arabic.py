"""Arabic normalization for matching (not for display)."""

from __future__ import annotations

import re

DIACRITICS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # + tatweel
_ALEF = re.compile("[إأآٱ]")
_NON_LETTER = re.compile(r"[^ء-ي\s]")


def normalize(text: str) -> str:
    """Strip diacritics and punctuation; unify alef, alef maqsura and ta marbuta."""
    s = _ALEF.sub("ا", DIACRITICS.sub("", text)).replace("ى", "ي").replace("ة", "ه")
    return " ".join(_NON_LETTER.sub(" ", s).split())

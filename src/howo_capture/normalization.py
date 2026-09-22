from __future__ import annotations

import hashlib
import re
import unicodedata


_NON_ALNUM = re.compile(r"[^A-Z0-9]+")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def normalize_part_number(value: str | None) -> str:
    """Return a comparison form without altering the stored raw value."""
    if not value:
        return ""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return _NON_ALNUM.sub("", ascii_value.upper())


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    words = _NON_WORD.sub(" ", ascii_value.lower()).split()
    return " ".join(words)


def stable_id(prefix: str, *parts: object, length: int = 20) -> str:
    material = "\x1f".join("" if part is None else str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"

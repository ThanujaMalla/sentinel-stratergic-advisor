from __future__ import annotations

import hashlib
import re


def normalize_text(value: object) -> str:
    if value is None:
        return ''
    text = str(value)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

"""
🛡️ Per-Cortex Rate Limit — protects against runaway costs.

Default limits (per user, per cortex, per 60-second window):
  - visual    : 10 images
  - video     : 3 videos
  - audio     : 20 audio clips
  - narrative : 30 text generations
  - code      : 60 turns (existing rate-limit applies separately)

Owner can override via env: ZENREX_CORTEX_RATE_LIMIT_<CORTEX>_PER_MIN.
"""
from __future__ import annotations

import os
import time
from typing import Dict, Tuple

_BUCKETS: Dict[Tuple[str, str], list] = {}

_DEFAULTS = {
    "visual": 10,
    "video": 3,
    "audio": 20,
    "narrative": 30,
    "code": 60,
}

_WINDOW_SEC = 60


def _limit_for(cortex: str) -> int:
    env_k = f"ZENREX_CORTEX_RATE_LIMIT_{cortex.upper()}_PER_MIN"
    try:
        v = int(os.environ.get(env_k, "0"))
        if v > 0:
            return v
    except Exception:
        pass
    return _DEFAULTS.get(cortex, 30)


def check_and_record(user_id: str, cortex: str) -> Tuple[bool, int, int]:
    """Return (allowed, current_count_in_window, limit).

    If allowed → records the hit. If denied → does not record.
    """
    if not user_id:
        return True, 0, _limit_for(cortex)
    key = (user_id, cortex)
    now = time.time()
    bucket = _BUCKETS.setdefault(key, [])
    cutoff = now - _WINDOW_SEC
    # Drop expired
    bucket[:] = [t for t in bucket if t > cutoff]
    limit = _limit_for(cortex)
    if len(bucket) >= limit:
        return False, len(bucket), limit
    bucket.append(now)
    return True, len(bucket), limit

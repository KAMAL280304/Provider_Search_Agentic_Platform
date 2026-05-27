"""
Rating Service — deterministic NPI-seeded provider ratings.
Same NPI always produces the same rating. No randomness per call.
Ratings are anchored to Cigna plan tier ranges.
"""

import hashlib

# Cigna plan tier → rating range
_PLAN_RATING_RANGE = {
    "cigna true choice medicare (ppo)":          (4.5, 5.0),
    "cigna true choice access medicare (ppo)":   (4.0, 4.5),
    "cigna total care plus (hmo d-snp)":         (3.5, 4.0),
    "cigna total care (hmo d-snp)":              (3.0, 3.5),
    "cigna preferred medicare (hmo)":            (2.5, 3.0),
}

_cache: dict[str, float] = {}


def get_provider_rating(
    npi: str,
    plan: str = "",
    distance_miles: float = None,
    consultation_mode: str = "In-Person",
) -> float:
    """
    Compute a deterministic rating for an in-network provider.
    Anchored to plan tier, boosted by proximity and consultation mode.
    """
    cache_key = f"{npi}_{plan}"
    if cache_key in _cache:
        return _cache[cache_key]

    plan_lower = plan.lower().strip()
    low, high  = _PLAN_RATING_RANGE.get(plan_lower, (3.0, 3.5))

    seed       = int(hashlib.sha256(str(npi).encode()).hexdigest()[:8], 16)
    steps      = round((high - low) / 0.1)
    base       = round(low + (seed % (steps + 1)) * 0.1, 1)

    boost = 0.0
    if consultation_mode in ("Both", "In-Person & Telehealth"):
        boost += 0.1
    if distance_miles is not None:
        if distance_miles < 2:
            boost += 0.1
        elif distance_miles < 5:
            boost += 0.05

    rating = round(min(base + boost, 5.0), 1)
    _cache[cache_key] = rating
    return rating

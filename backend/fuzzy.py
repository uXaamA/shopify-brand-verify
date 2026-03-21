import re
from Levenshtein import ratio

# Similarity threshold for typo detection (Nikee vs Nike)
TYPO_THRESHOLD = 0.80

# Words that are ignored when extracting the base brand name
# "Nike Clearance" → base = "Nike"
# "Nike India"     → base = "Nike"
# "Nike.asia"      → base = "Nike"
IGNORED_SUFFIXES = {
    # Geography
    "india", "pakistan", "asia", "global", "international", "worldwide",
    "usa", "uk", "eu", "europe", "africa", "australia", "canada",
    "karachi", "lahore", "dubai", "london",
    # Business words
    "clearance", "sale", "outlet", "store", "shop", "official",
    "original", "authentic", "verified", "certified", "authorized",
    "wholesale", "retail", "market", "bazaar", "deals", "discount",
    "online", "digital", "express", "direct", "hub", "zone",
    "collection", "collections", "limited", "exclusive", "premium",
    "pro", "plus", "lite", "max", "mini", "official", "real",
    "pk", "co", "ltd", "llc", "inc", "corp", "brand", "brands",
}


def extract_base(name: str) -> str:
    """
    Extract the core brand word from a name.

    Examples:
        "Nike Clearance"   → "nike"
        "Nike.asia"        → "nike"
        "Nike India"       → "nike"
        "Nike.pk"          → "nike"
        "Adidas Official"  → "adidas"
        "PUMA"             → "puma"
        "Nike"             → "nike"
    """
    # Lowercase and replace separators with spaces
    name = name.lower().strip()
    name = re.sub(r'[.\-_/\\]', ' ', name)

    # Split into words
    words = name.split()

    # Remove ignored suffix words from the end
    # Keep removing from the right until we hit a non-ignored word
    while len(words) > 1 and words[-1] in IGNORED_SUFFIXES:
        words.pop()

    # Return the remaining words joined (handles multi-word brands like "Louis Vuitton")
    return " ".join(words)


def check_conflict(new_name: str, existing_names: list[str]) -> dict:
    """
    Check if a new brand name conflicts with any existing registered brand.

    Two-level check:
    1. BASE WORD MATCH — "Nike.clearance" → base "nike" == base "nike" → BLOCKED
    2. TYPO CHECK      — "Nikee" vs "Nike" → 89% similar → BLOCKED

    Returns:
    {
        "conflict": True/False,
        "conflicting_brand": "Nike" or None,
        "reason": "base_match" or "typo" or None,
        "message": "human readable explanation"
    }
    """
    new_base = extract_base(new_name)

    for existing in existing_names:
        existing_base = extract_base(existing)

        # ── Level 1: Base word exact match ──
        # Nike vs Nike.clearance → "nike" == "nike" → BLOCKED
        if new_base == existing_base:
            return {
                "conflict":          True,
                "conflicting_brand": existing,
                "reason":            "base_match",
                "message": (
                    f"'{new_name}' is not allowed because '{existing}' is already registered. "
                    f"Only one seller can own the '{existing_base.title()}' brand. "
                    f"If you are the official owner, use 'Claim Official Ownership'."
                )
            }

        # ── Level 2: Typo / misspelling check ──
        # Nikee vs Nike → 89% similar → BLOCKED
        similarity = ratio(new_base, existing_base)
        if similarity >= TYPO_THRESHOLD:
            return {
                "conflict":          True,
                "conflicting_brand": existing,
                "reason":            "typo",
                "similarity":        round(similarity, 2),
                "message": (
                    f"'{new_name}' is too similar to the already-registered brand '{existing}' "
                    f"({round(similarity * 100)}% match). "
                    f"If you are the official owner, use 'Claim Official Ownership'."
                )
            }

    return {
        "conflict":          False,
        "conflicting_brand": None,
        "reason":            None,
        "message":           f"'{new_name}' is available for registration."
    }
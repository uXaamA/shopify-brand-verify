import re
from Levenshtein import ratio
from typing import List, Optional

# Similarity threshold for typo detection
TYPO_THRESHOLD = 0.82


def normalize(name: str) -> str:
    """
    Normalize a brand name for comparison.
    Also replaces common number-for-letter substitutions.
    Nike.pak → nikepak
    N1ke → nike
    Ph4ntom → phantom
    """
    name = name.lower().strip()
    # Remove all separators
    name = re.sub(r'[.\-_/\\ ]', '', name)
    # Replace common number substitutions
    name = name.replace('1', 'i')
    name = name.replace('3', 'e')
    name = name.replace('4', 'a')
    name = name.replace('0', 'o')
    name = name.replace('5', 's')
    name = name.replace('7', 't')
    return name


def check_conflict(new_name: str, existing_names: List[str]) -> dict:
    """
    Check if a new brand name conflicts with any registered brand.

    Three-level check:

    Level 1 — EXACT normalized match
        "Nike" vs "Nike" → "nike" == "nike" → BLOCK

    Level 2 — CONTAINMENT check  
        Registered brand name appears inside the new name
        "Nike" registered → "Nike.pak" normalized = "nikepak"
        "nike" in "nikepak" → YES → BLOCK
        This catches: Nike.pak, Nike.india, NikeOfficial, NikeClearance etc.

    Level 3 — TYPO / SIMILARITY check
        Catches misspellings like Nikee, N1ke, Adiddas
        Uses Levenshtein ratio on normalized names
        Threshold: 82%
    """
    new_normalized = normalize(new_name)

    for existing in existing_names:
        existing_normalized = normalize(existing)

        # ── Level 1: Exact normalized match ──
        if new_normalized == existing_normalized:
            return {
                "conflict":          True,
                "conflicting_brand": existing,
                "reason":            "exact_match",
                "message": (
                    f"'{new_name}' is already registered. "
                    f"If you are the official owner, use 'Claim Official Ownership'."
                )
            }

        # ── Level 2: Containment check ──
        # If registered brand name appears inside the new name
        # "nike" in "nikepak" → True
        # "nike" in "nikeclearance" → True
        # "nike" in "nikeofficial" → True
        # ── Level 2: Containment check ──

        # ── Starts-with check ──
        # "phantomwearpakistan" starts with "phantomwears"? No
        # but "phantomwears" starts with "phantomwear"? Yes → BLOCK
        # Catches: phantomwear.anything when phantomwears is registered
        if (new_normalized.startswith(existing_normalized) or
                existing_normalized.startswith(new_normalized)):
            return {
                "conflict":          True,
                "conflicting_brand": existing,
                "reason":            "starts_with",
                "message": (
                    f"'{new_name}' is not allowed because it starts with the "
                    f"registered brand '{existing}'. Only one seller can own "
                    f"the '{existing}' brand. If you are the official owner, "
                    f"use 'Claim Official Ownership'."
                )
            }

        if existing_normalized in new_normalized:
            return {
                "conflict":          True,
                "conflicting_brand": existing,
                "reason":            "contains_brand",
                "message": (
                    f"'{new_name}' is not allowed because it contains the "
                    f"registered brand '{existing}'. Only one seller can own "
                    f"the '{existing}' brand. If you are the official owner, "
                    f"use 'Claim Official Ownership'."
                )
            }

        # Also check if new name is almost same as existing
        # "phantomwear" vs "phantomwears" — one char difference
        if new_normalized in existing_normalized:
            return {
                "conflict":          True,
                "conflicting_brand": existing,
                "reason":            "partial_match",
                "message": (
                    f"'{new_name}' is too similar to the registered brand "
                    f"'{existing}'. If you are the official owner, use "
                    f"'Claim Official Ownership'."
                )
            }

        # ── Level 3: Typo / similarity check ──
        similarity = ratio(new_normalized, existing_normalized)
        if similarity >= TYPO_THRESHOLD:
            return {
                "conflict":          True,
                "conflicting_brand": existing,
                "reason":            "typo",
                "similarity":        round(similarity, 2),
                "message": (
                    f"'{new_name}' is too similar to the registered brand '{existing}' "
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
















# import re
# from Levenshtein import ratio

# # Similarity threshold for typo detection (Nikee vs Nike)
# TYPO_THRESHOLD = 0.80

# # Words that are ignored when extracting the base brand name
# # "Nike Clearance" → base = "Nike"
# # "Nike India"     → base = "Nike"
# # "Nike.asia"      → base = "Nike"
# IGNORED_SUFFIXES = {
#     # Geography
#     "india", "pakistan", "asia", "global", "international", "worldwide",
#     "usa", "uk", "eu", "europe", "africa", "australia", "canada",
#     "karachi", "lahore", "dubai", "london", "pak",
#     # Business words
#     "clearance", "sale", "outlet", "store", "shop", "official",
#     "original", "authentic", "verified", "certified", "authorized",
#     "wholesale", "retail", "market", "bazaar", "deals", "discount",
#     "online", "digital", "express", "direct", "hub", "zone",
#     "collection", "collections", "limited", "exclusive", "premium",
#     "pro", "plus", "lite", "max", "mini", "official", "real",
#     "pk", "co", "ltd", "llc", "inc", "corp", "brand", "brands",
# }


# def extract_base(name: str) -> str:
#     """
#     Extract the core brand word from a name.

#     Examples:
#         "Nike.pak"       → "nike"
#         "Nike Clearance" → "nike"
#         "Nike.asia"      → "nike"
#         "Nike India"     → "nike"
#         "Adidas Official"→ "adidas"
#         "Louis Vuitton"  → "louis vuitton"  (multi-word brand kept)
#     """
#     # Lowercase
#     name = name.lower().strip()

#     # Replace separators (dots, dashes, underscores) with spaces
#     name = re.sub(r'[.\-_/\\]', ' ', name)

#     # Split into words
#     words = name.split()

#     # Remove ALL ignored words from anywhere in the name
#     # not just the end — "Nike Official Store" → ["nike"]
#     core_words = [w for w in words if w not in IGNORED_SUFFIXES]

#     # If nothing left, return original first word
#     if not core_words:
#         return words[0] if words else name

#     # Join remaining core words
#     return " ".join(core_words)


# def check_conflict(new_name: str, existing_names: list[str]) -> dict:
#     """
#     Check if a new brand name conflicts with any existing registered brand.

#     Two-level check:
#     1. BASE WORD MATCH — "Nike.clearance" → base "nike" == base "nike" → BLOCKED
#     2. TYPO CHECK      — "Nikee" vs "Nike" → 89% similar → BLOCKED

#     Returns:
#     {
#         "conflict": True/False,
#         "conflicting_brand": "Nike" or None,
#         "reason": "base_match" or "typo" or None,
#         "message": "human readable explanation"
#     }
#     """
#     new_base = extract_base(new_name)

#     for existing in existing_names:
#         existing_base = extract_base(existing)

#         # ── Level 1: Base word exact match ──
#         # Nike vs Nike.clearance → "nike" == "nike" → BLOCKED
#         if new_base == existing_base:
#             return {
#                 "conflict":          True,
#                 "conflicting_brand": existing,
#                 "reason":            "base_match",
#                 "message": (
#                     f"'{new_name}' is not allowed because '{existing}' is already registered. "
#                     f"Only one seller can own the '{existing_base.title()}' brand. "
#                     f"If you are the official owner, use 'Claim Official Ownership'."
#                 )
#             }

#         # ── Level 2: Typo / misspelling check ──
#         # Nikee vs Nike → 89% similar → BLOCKED
#         similarity = ratio(new_base, existing_base)
#         if similarity >= TYPO_THRESHOLD:
#             return {
#                 "conflict":          True,
#                 "conflicting_brand": existing,
#                 "reason":            "typo",
#                 "similarity":        round(similarity, 2),
#                 "message": (
#                     f"'{new_name}' is too similar to the already-registered brand '{existing}' "
#                     f"({round(similarity * 100)}% match). "
#                     f"If you are the official owner, use 'Claim Official Ownership'."
#                 )
#             }

#     return {
#         "conflict":          False,
#         "conflicting_brand": None,
#         "reason":            None,
#         "message":           f"'{new_name}' is available for registration."
#     }
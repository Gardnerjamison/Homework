"""Filtering logic that keeps *full miniatures/units* and throws out
bits, body parts, accessories, paper products, merch and recasts.

The whole point of the app: you search for a unit (e.g. "Necron Warriors")
and you only want listings that are an actual model/unit you could field
-- in any condition (sealed, opened, built, painted) -- not a bag of
spare arms or a codex.

The matching is deliberately a bit aggressive: when in doubt it is better
to drop a borderline listing than to make you wade through pages of bits.
Every category can be toggled off in config.json, and `allow_terms` lets
you whitelist a word that would otherwise get a listing dropped.
"""

import re

# --- Term lists -------------------------------------------------------------
# Single words are matched on word boundaries (so "head" won't trip on
# "Deathwing"); multi-word phrases are matched as substrings.

# Always dropped -- these are never a model, regardless of config toggles.
ALWAYS_EXCLUDE = [
    "box only", "empty box", "instructions only", "instruction only",
    "manual only", "sprue only", "art only", "poster only", "case only",
]

BITS = [
    "bits", "bitz", "spares", "spare part", "spare parts",
    "loose bits", "conversion bits", "bits lot", "bitz lot",
    "job lot of bits", "lot of bits",
]

BODYPARTS = [
    "arm", "arms", "leg", "legs", "torso", "torsos",
    "head", "heads", "shoulder pad", "shoulder pads",
    "pauldron", "pauldrons", "backpack", "backpacks",
    "helmet", "helmets", "hands",
]

ACCESSORIES = [
    "movement tray", "movement trays", "objective marker",
    "objective markers", "token", "tokens", "counter", "counters",
    "dice", "carry case", "carrying case", "battle foam", "foam tray",
    "kr multicase", "magnet", "magnets", "transfer", "transfers",
    "decal", "decals", "sticker", "stickers", "sleeve", "sleeves",
    "paint", "paints", "brush", "brushes", "primer",
    "base only", "bases only", "empty base", "empty bases",
    # merch / not-a-model
    "t-shirt", "tshirt", "hoodie", "mug", "keyring", "keychain",
    "pin badge", "funko", "canvas", "wall art", "artwork", "poster",
]

BOOKS_PAPER = [
    "codex", "codexes", "rulebook", "rule book", "rulebooks", "rules",
    "datacard", "datacards", "data card", "data cards", "card", "cards",
    "instruction", "instructions", "manual", "leaflet", "booklet",
    "supplement", "novel", "magazine", "white dwarf", "battletome",
]

RECAST_3DPRINT = [
    "recast", "recasts", "proxy", "proxies",
    "3d print", "3d printed", "3dprint", "3d-print",
    "stl", "resin print", "resin printed", "printed minis",
    "printed miniature", "printed miniatures", "printed model",
    "printed models", "custom cast", "not gw", "not games workshop",
    "unofficial", "fan made", "fanmade",
]

CATEGORY_TERMS = {
    "exclude_bits": BITS,
    "exclude_bodyparts": BODYPARTS,
    "exclude_accessories": ACCESSORIES,
    "exclude_books_paper": BOOKS_PAPER,
    "exclude_recast_3dprint": RECAST_3DPRINT,
}

DEFAULT_FILTER_CONFIG = {
    "exclude_bits": True,
    "exclude_bodyparts": True,
    "exclude_accessories": True,
    "exclude_books_paper": True,
    "exclude_recast_3dprint": True,
    "extra_exclude_terms": [],
    "allow_terms": [],
}


def _first_match(title, terms):
    """Return the first term in `terms` that occurs in `title`, else None.

    `title` must already be lowercased. Single words use word boundaries;
    phrases (containing a space or hyphen) use substring matching.
    """
    for term in terms:
        term = term.lower().strip()
        if not term:
            continue
        if " " in term or "-" in term:
            if term in title:
                return term
        elif re.search(r"\b" + re.escape(term) + r"\b", title):
            return term
    return None


def build_exclude_terms(filter_config):
    """Assemble the active exclusion list from the config toggles."""
    cfg = {**DEFAULT_FILTER_CONFIG, **(filter_config or {})}
    terms = list(ALWAYS_EXCLUDE)
    for key, term_list in CATEGORY_TERMS.items():
        if cfg.get(key, True):
            terms.extend(term_list)
    terms.extend(cfg.get("extra_exclude_terms", []) or [])
    return terms


def classify(title, filter_config=None):
    """Decide whether a listing title is a keepable full model.

    Returns (keep: bool, reason: str). When dropped, `reason` is the term
    that triggered the exclusion so the UI can explain itself.
    """
    cfg = {**DEFAULT_FILTER_CONFIG, **(filter_config or {})}
    low = (title or "").lower()

    allow_hit = _first_match(low, cfg.get("allow_terms", []) or [])
    if allow_hit:
        return True, f"allow:{allow_hit}"

    hit = _first_match(low, build_exclude_terms(cfg))
    if hit:
        return False, hit
    return True, ""


def filter_items(items, filter_config=None):
    """Split a list of normalized listing dicts into kept / dropped.

    Each item dict is expected to have a "title" key. Returns
    (kept, dropped) where dropped items get a "_drop_reason" added.
    """
    kept, dropped = [], []
    for item in items:
        keep, reason = classify(item.get("title", ""), filter_config)
        if keep:
            kept.append(item)
        else:
            item = {**item, "_drop_reason": reason}
            dropped.append(item)
    return kept, dropped

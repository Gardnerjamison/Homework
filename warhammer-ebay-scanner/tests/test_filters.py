"""Tests for the full-unit-only filter -- the core of the app."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ebay_scanner.filters import classify, filter_items


# Titles that ARE full units -> should be kept.
KEEP = [
    "Warhammer 40k Necron Warriors x10 New in Box Sealed",
    "Space Marine Intercessors Squad Built & Primed",
    "Citadel Custodian Guard Pro Painted Adeptus Custodes",
    "Necron Lychguard 5 Models Assembled Unpainted",
    "Warhammer 40,000 Terminator Squad NIB OOP",
    "Tyranid Termagants 12 models on sprue new",
    "Tau Fire Warriors Strike Team boxed used complete",
]

# Titles that are NOT a full model -> should be dropped.
DROP = [
    "Space Marine Bits - Bolters and Arms Lot",
    "Necron Warriors spare heads x20 bitz",
    "Warhammer 40k Codex Necrons 9th Edition Hardback",
    "Custodes Datacards Data Cards Set",
    "Space Marine Shoulder Pads Ultramarines Bitz",
    "3D Printed Necron Warriors Proxy x10 Resin",
    "Recast Custodian Guard 5 models",
    "Warhammer Movement Trays Magnetic Set",
    "Citadel Paint Set Base Paints Necron",
    "Empty Box only Necron Warriors no models",
    "Lot of backpacks and arms space marines",
    "Warhammer 40k Objective Markers tokens",
    "Space Marine T-Shirt Ultramarines XL",
]


def test_keep_full_units():
    for title in KEEP:
        keep, reason = classify(title)
        assert keep, f"should KEEP but dropped ({reason!r}): {title}"


def test_drop_non_models():
    for title in DROP:
        keep, reason = classify(title)
        assert not keep, f"should DROP but kept: {title}"


def test_allow_terms_override():
    title = "Necron Overlord with extra heads"
    assert not classify(title)[0]  # "heads" -> dropped by default
    keep, reason = classify(title, {"allow_terms": ["heads"]})
    assert keep and reason.startswith("allow:")


def test_toggle_off_category():
    title = "Warhammer 40k Codex Necrons"
    assert not classify(title)[0]
    # Turn off the books filter -> now kept.
    assert classify(title, {"exclude_books_paper": False})[0]


def test_extra_exclude_terms():
    title = "Necron Warriors weird custom thing"
    assert classify(title)[0]
    assert not classify(title, {"extra_exclude_terms": ["weird custom"]})[0]


def test_filter_items_split():
    items = [{"title": t} for t in KEEP + DROP]
    kept, dropped = filter_items(items)
    assert len(kept) == len(KEEP)
    assert len(dropped) == len(DROP)
    assert all("_drop_reason" in d for d in dropped)

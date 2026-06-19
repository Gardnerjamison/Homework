"""Load and persist the app config (which minis to watch + filter settings)."""

import json
import os
import shutil

HERE = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
EXAMPLE_PATH = os.path.join(HERE, "config.example.json")

DEFAULTS = {
    "marketplace_id": "EBAY_US",
    "currency": "USD",
    "environment": "production",
    # 180349 = eBay "Toys & Hobbies > ... > Miniatures, War Games".
    # Restricting to this category strips out a lot of paint/book/merch noise
    # before our keyword filter even runs. Empty the list to search all.
    "category_ids": ["180349"],
    "results_per_search": 50,
    "sort": "newlyListed",
    "searches": [],
    "filters": {
        "exclude_bits": True,
        "exclude_bodyparts": True,
        "exclude_accessories": True,
        "exclude_books_paper": True,
        "exclude_recast_3dprint": True,
        "extra_exclude_terms": [],
        "allow_terms": [],
    },
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        if os.path.exists(EXAMPLE_PATH):
            shutil.copy(EXAMPLE_PATH, CONFIG_PATH)
        else:
            save_config(DEFAULTS)
    with open(CONFIG_PATH) as fh:
        cfg = json.load(fh)
    merged = {**DEFAULTS, **cfg}
    merged["filters"] = {**DEFAULTS["filters"], **(cfg.get("filters") or {})}
    return merged


def save_config(cfg):
    with open(CONFIG_PATH, "w") as fh:
        json.dump(cfg, fh, indent=2)

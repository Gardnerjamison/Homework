"""Flask web app: dashboard of watched Warhammer minis with full-unit-only
eBay results."""

import os
import time

from flask import Flask, jsonify, render_template, request

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

from .config import load_config, save_config
from .ebay_client import EbayClient, EbayError
from .filters import filter_items

app = Flask(__name__)

# Tiny in-memory cache so refreshing the page / re-rendering doesn't hammer
# the eBay API. Keyed by the search params; expires after CACHE_TTL seconds.
_CACHE = {}
CACHE_TTL = 300


def _client(cfg):
    return EbayClient(
        client_id=os.environ.get("EBAY_CLIENT_ID"),
        client_secret=os.environ.get("EBAY_CLIENT_SECRET"),
        marketplace_id=cfg.get("marketplace_id", "EBAY_US"),
        environment=cfg.get("environment", "production"),
        currency=cfg.get("currency", "USD"),
    )


def _run_search(client, cfg, search, force=False):
    key = (
        search.get("query"), cfg.get("results_per_search"),
        tuple(cfg.get("category_ids") or []), search.get("min_price"),
        search.get("max_price"), cfg.get("sort"),
    )
    now = time.time()
    if not force and key in _CACHE and _CACHE[key][0] > now:
        raw = _CACHE[key][1]
    else:
        raw = client.search(
            query=search["query"],
            limit=cfg.get("results_per_search", 50),
            category_ids=cfg.get("category_ids"),
            min_price=search.get("min_price"),
            max_price=search.get("max_price"),
            sort=cfg.get("sort", "newlyListed"),
        )
        _CACHE[key] = (now + CACHE_TTL, raw)

    kept, dropped = filter_items(raw, cfg.get("filters"))
    return {
        "name": search.get("name") or search.get("query"),
        "query": search.get("query"),
        "kept": kept,
        "total": len(raw),
        "filtered_out": len(dropped),
    }


@app.route("/")
def index():
    cfg = load_config()
    creds_ok = bool(os.environ.get("EBAY_CLIENT_ID") and os.environ.get("EBAY_CLIENT_SECRET"))
    return render_template("index.html", cfg=cfg, creds_ok=creds_ok)


@app.route("/api/results")
def api_results():
    cfg = load_config()
    force = request.args.get("refresh") == "1"
    try:
        client = _client(cfg)
    except EbayError as exc:
        return jsonify({"error": str(exc)}), 400

    groups, errors = [], []
    for search in cfg.get("searches", []):
        if not search.get("query"):
            continue
        try:
            groups.append(_run_search(client, cfg, search, force=force))
        except EbayError as exc:
            errors.append({"name": search.get("name"), "error": str(exc)})
    return jsonify({"groups": groups, "errors": errors})


@app.route("/api/searches", methods=["POST"])
def add_search():
    cfg = load_config()
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    def _price(v):
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    cfg.setdefault("searches", []).append({
        "name": (data.get("name") or query).strip(),
        "query": query,
        "min_price": _price(data.get("min_price")),
        "max_price": _price(data.get("max_price")),
    })
    save_config(cfg)
    return jsonify({"ok": True, "searches": cfg["searches"]})


@app.route("/api/searches/<int:index>", methods=["DELETE"])
def delete_search(index):
    cfg = load_config()
    searches = cfg.get("searches", [])
    if 0 <= index < len(searches):
        searches.pop(index)
        save_config(cfg)
        return jsonify({"ok": True, "searches": searches})
    return jsonify({"error": "invalid index"}), 404


def main():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()

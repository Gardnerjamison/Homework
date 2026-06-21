# ⚔️ Warhammer eBay Scanner

Scan eBay for the Warhammer minis you actually want — **full units/models in
any condition** (sealed, opened, built, painted) — and automatically hide the
noise: loose **bits**, spare **arms/heads/shoulder pads**, **codexes & cards**,
**paints**, **movement trays**, **3D-printed proxies & recasts**, and merch.

You add the units you care about once; the app searches eBay for each, filters
out everything that isn't a model, and shows the survivors as a clean grid with
images, prices and condition.

![local web app, dark grid of listing cards] <!-- screenshot once you run it -->

---

## How it works

- Two interchangeable backends fetch listings (pick one in `config.json`):
  - **`scrape`** (default) — parses eBay's normal search page. **No account
    needed, works out of the box.**
  - **`api`** — eBay's official **Browse API** (cleaner data, but needs free
    developer keys; see below).
- Restricts to eBay's *Miniatures, War Games* category to cut noise, then runs
  a keyword filter (`ebay_scanner/filters.py`) to drop non-models.
- A small Flask app serves a dashboard at `http://127.0.0.1:5000`.

## Setup

```bash
cd warhammer-ebay-scanner
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
python run.py
```
Open <http://127.0.0.1:5000>. Type a unit (e.g. *Necron Warriors*, *Custodian
Guard*, *Terminator Squad*), optionally a max price, and hit **Watch**.

That's it — the default `scrape` backend needs no keys.

> **Run it from a normal home connection.** eBay tends to return `403` to
> datacenter / VPN / cloud IPs. If every search errors with a 403, that's why.

### Optional: use the official API instead of scraping

The API gives cleaner data (a real condition field, seller feedback) and is the
sanctioned route. To use it:

1. Get free keys at <https://developer.ebay.com> — create a **Production**
   keyset and copy the **App ID (Client ID)** and **Cert ID (Client Secret)**.
2. `cp .env.example .env` and paste them in (or export `EBAY_CLIENT_ID` /
   `EBAY_CLIENT_SECRET`).
3. Set `"backend": "api"` in `config.json`.

You can switch between `scrape` and `api` anytime — same dashboard, same filters.

## Using it

- **Watch** adds a search; results appear as cards (click to open the listing).
- Each group shows `N kept · M junk hidden` so you can see how much it filtered.
- **✕** stops watching a unit. **⟳ Refresh** forces a fresh pull (results are
  cached for 5 min to be kind to the API).
- Your watched units live in `config.json` (created on first run, git-ignored).

## Tuning the filter

Edit the `filters` block in `config.json`:

| Key | Hides |
|---|---|
| `exclude_bits` | bits, bitz, spares, conversion bits |
| `exclude_bodyparts` | arms, legs, heads, torsos, shoulder pads, backpacks… |
| `exclude_accessories` | movement trays, tokens, dice, paints, magnets, cases, merch |
| `exclude_books_paper` | codexes, rulebooks, datacards |
| `exclude_recast_3dprint` | recasts, proxies, STL/3D-printed, "not GW" |
| `extra_exclude_terms` | your own words to ban |
| `allow_terms` | whitelist a word so a listing is **always kept** (overrides above) |

Example — you collect a unit whose name contains "wings", and you don't mind
3D prints:
```json
"filters": {
  "exclude_recast_3dprint": false,
  "allow_terms": ["wings"]
}
```

Other `config.json` knobs: `marketplace_id` (`EBAY_GB`, `EBAY_DE`, …),
`currency`, `results_per_search`, `sort` (`newlyListed`, `price`),
`category_ids` (empty the list to search all of eBay).

## Tests
```bash
pip install pytest && python -m pytest tests/
```
`tests/test_filters.py` documents exactly what gets kept vs dropped — the best
place to look if a listing is being filtered when it shouldn't be.

## Notes
- Keys, `config.json` and the token cache are git-ignored — nothing secret is
  committed.
- The filter is intentionally aggressive (better to miss a borderline listing
  than show you a page of bits). Loosen it via the toggles / `allow_terms`.
- The `scrape` backend reads eBay's public search page. That's a gray area
  under eBay's Terms of Service — fine for light personal use, but keep request
  volume low (results are cached 5 min). If eBay restyles their results page
  and parsing breaks, update the selectors in `scraper.parse_search_html`
  (covered by `tests/test_scraper.py`). For heavy or commercial use, switch to
  the official API backend.

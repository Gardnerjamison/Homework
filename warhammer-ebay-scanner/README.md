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

- Uses eBay's official **Browse API** (OAuth2 client-credentials flow — no
  personal login, just free app keys).
- Restricts to eBay's *Miniatures, War Games* category to cut noise, then runs
  a keyword filter (`ebay_scanner/filters.py`) to drop non-models.
- A small Flask app serves a dashboard at `http://127.0.0.1:5000`.

## Setup (one time, ~10 min)

### 1. Get free eBay API keys
1. Go to <https://developer.ebay.com> and create an account.
2. Create a **Production** keyset (Application Keys).
3. Copy the **App ID (Client ID)** and **Cert ID (Client Secret)**.

### 2. Install
```bash
cd warhammer-ebay-scanner
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

### 3. Add your keys
```bash
cp .env.example .env
# edit .env and paste your App ID / Cert ID
```
(Or export `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` as environment variables.)

### 4. Run
```bash
python run.py
```
Open <http://127.0.0.1:5000>. Type a unit (e.g. *Necron Warriors*, *Custodian
Guard*, *Terminator Squad*), optionally a max price, and hit **Watch**.

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

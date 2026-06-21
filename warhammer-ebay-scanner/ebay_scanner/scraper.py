"""HTML-scraping backend for eBay search.

Drop-in alternative to EbayClient for when you don't have API keys: it
fetches eBay's normal search-results page and parses the listings out of the
HTML, returning the *same* normalized dicts as `EbayClient.search`, so the
filters and the web UI work unchanged.

Trade-offs vs the official API:
  * No account/approval needed.
  * Against eBay's Terms of Service (gray area for light personal use) and
    more fragile -- if eBay restyles their results page, the selectors here
    may need updating (see `parse_search_html`).
  * Condition is read from the page's text label rather than a clean field.

Runs fine from a home/residential IP; eBay tends to 403 datacenter IPs.
"""

import re
import urllib.parse

import requests

MARKET_DOMAINS = {
    "EBAY_US": "www.ebay.com",
    "EBAY_GB": "www.ebay.co.uk",
    "EBAY_DE": "www.ebay.de",
    "EBAY_CA": "www.ebay.ca",
    "EBAY_AU": "www.ebay.com.au",
    "EBAY_IT": "www.ebay.it",
    "EBAY_FR": "www.ebay.fr",
    "EBAY_ES": "www.ebay.es",
}

# eBay's `_sop` (sort) codes.
SORT_CODES = {
    "newlyListed": "10",
    "endingSoonest": "1",
    "price": "15",          # price + shipping: lowest first
    "-price": "16",         # price + shipping: highest first
    "bestMatch": "12",
}

CURRENCY_SYMBOLS = [
    ("C $", "CAD"), ("AU $", "AUD"), ("US $", "USD"),
    ("$", "USD"), ("£", "GBP"), ("€", "EUR"),
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class ScraperError(RuntimeError):
    pass


def _parse_price(text):
    """('$24.99' | '$10.00 to $20.00') -> (24.99, 'USD'). Returns first value."""
    if not text:
        return None, None
    currency = None
    for sym, code in CURRENCY_SYMBOLS:
        if sym in text:
            currency = code
            break
    m = re.search(r"\d[\d,]*\.\d{2}|\d[\d,]*", text)
    value = float(m.group().replace(",", "")) if m else None
    return value, currency


def _parse_shipping(text):
    if not text:
        return None
    if "free" in text.lower():
        return 0.0
    value, _ = _parse_price(text)
    return value


def _item_id_from_url(url):
    if not url:
        return None
    m = re.search(r"/itm/(?:[^/]+/)?(\d{6,})", url)
    return m.group(1) if m else None


def _text(node, selector):
    el = node.select_one(selector)
    return el.get_text(" ", strip=True) if el else ""


def parse_search_html(html):
    """Parse an eBay search-results page into normalized listing dicts.

    Pure function (no network) so it can be unit-tested against fixtures.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select("li.s-item") or soup.select("li.s-card") or soup.select(".s-item")
    items = []
    for node in nodes:
        title = _text(node, ".s-item__title") or _text(node, ".s-card__title")
        # The first tile is often a "Shop on eBay" placeholder.
        if not title or title.lower() in ("shop on ebay", "results"):
            continue

        link_el = node.select_one("a.s-item__link") or node.select_one("a")
        url = link_el.get("href") if link_el else None
        if url:
            url = url.split("?")[0]

        price_val, currency = _parse_price(
            _text(node, ".s-item__price") or _text(node, ".s-card__price"))

        img_el = node.select_one(".s-item__image-wrapper img") or node.select_one("img")
        image = None
        if img_el:
            image = img_el.get("src") or img_el.get("data-src")

        condition = (_text(node, ".SECONDARY_INFO")
                     or _text(node, ".s-item__subtitle")
                     or "Not specified")
        shipping = _parse_shipping(
            _text(node, ".s-item__shipping") or _text(node, ".s-item__logisticsCost"))
        location = (_text(node, ".s-item__location")
                    or _text(node, ".s-item__itemLocation") or None)

        items.append({
            "itemId": _item_id_from_url(url),
            "title": title,
            "price": price_val,
            "currency": currency,
            "shipping": shipping,
            "condition": condition or "Not specified",
            "conditionId": None,
            "url": url,
            "image": image,
            "seller": None,
            "feedbackPct": None,
            "location": location,
            "buyingOptions": [],
        })
    return items


class ScraperClient:
    """Same interface as EbayClient.search, backed by HTML scraping."""

    def __init__(self, marketplace_id="EBAY_US", currency="USD", **_ignored):
        self.domain = MARKET_DOMAINS.get(marketplace_id, "www.ebay.com")
        self.currency = currency
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def search(self, query, limit=50, category_ids=None,
               min_price=None, max_price=None, sort="newlyListed"):
        params = {
            "_nkw": query,
            "_ipg": min(max(int(limit), 60), 240),  # items per page: 60/120/240
            "_sop": SORT_CODES.get(sort, "12"),
        }
        if category_ids:
            params["_sacat"] = str(category_ids[0])
        if min_price is not None:
            params["_udlo"] = min_price
        if max_price is not None:
            params["_udhi"] = max_price

        url = f"https://{self.domain}/sch/i.html?" + urllib.parse.urlencode(params)
        try:
            resp = self.session.get(url, timeout=30)
        except requests.RequestException as exc:
            raise ScraperError(f"eBay request failed: {exc}")
        if resp.status_code != 200:
            raise ScraperError(
                f"eBay returned HTTP {resp.status_code}. If this is a datacenter/"
                "VPN IP, eBay may be blocking it -- run from a home connection."
            )
        items = parse_search_html(resp.text)
        if not items and "s-item" not in resp.text and "s-card" not in resp.text:
            raise ScraperError(
                "Could not find any listings in the page -- eBay may have changed "
                "their layout (update selectors in scraper.parse_search_html)."
            )
        return items[:int(limit)]

"""Thin client for eBay's Browse API (the modern, supported search API).

Uses the OAuth2 *client credentials* flow (application token) -- that's all
that's needed for public listing search, no user login required.

Get free credentials at https://developer.ebay.com/ :
  1. Create an account, then create a "production" keyset.
  2. Note the App ID (Client ID) and Cert ID (Client Secret).
  3. Set them as env vars EBAY_CLIENT_ID / EBAY_CLIENT_SECRET
     (or put them in a .env file -- see README).
"""

import base64
import json
import os
import time

import requests

PROD_BASE = "https://api.ebay.com"
SANDBOX_BASE = "https://api.sandbox.ebay.com"
OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"
TOKEN_CACHE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".token_cache.json")


class EbayError(RuntimeError):
    pass


class EbayClient:
    def __init__(self, client_id, client_secret, marketplace_id="EBAY_US",
                 environment="production", currency="USD"):
        if not client_id or not client_secret:
            raise EbayError(
                "Missing eBay credentials. Set EBAY_CLIENT_ID and "
                "EBAY_CLIENT_SECRET (see README)."
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self.marketplace_id = marketplace_id
        self.currency = currency
        self.base = SANDBOX_BASE if environment == "sandbox" else PROD_BASE
        self._token = None
        self._token_expiry = 0
        self._load_cached_token()

    # --- OAuth ------------------------------------------------------------
    def _load_cached_token(self):
        try:
            with open(TOKEN_CACHE) as fh:
                data = json.load(fh)
            if data.get("client_id") == self.client_id and data.get("expiry", 0) > time.time() + 60:
                self._token = data["token"]
                self._token_expiry = data["expiry"]
        except (OSError, ValueError, KeyError):
            pass

    def _save_cached_token(self):
        try:
            with open(TOKEN_CACHE, "w") as fh:
                json.dump({
                    "client_id": self.client_id,
                    "token": self._token,
                    "expiry": self._token_expiry,
                }, fh)
        except OSError:
            pass

    def _get_token(self):
        if self._token and self._token_expiry > time.time() + 60:
            return self._token
        creds = f"{self.client_id}:{self.client_secret}".encode()
        headers = {
            "Authorization": "Basic " + base64.b64encode(creds).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        body = {"grant_type": "client_credentials", "scope": OAUTH_SCOPE}
        resp = requests.post(f"{self.base}/identity/v1/oauth2/token",
                             headers=headers, data=body, timeout=30)
        if resp.status_code != 200:
            raise EbayError(
                f"eBay OAuth failed ({resp.status_code}): {resp.text[:300]}"
            )
        data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + int(data.get("expires_in", 7200))
        self._save_cached_token()
        return self._token

    # --- Search -----------------------------------------------------------
    def _price_filter(self, min_price, max_price):
        if min_price is None and max_price is None:
            return None
        lo = "" if min_price is None else str(min_price)
        hi = "" if max_price is None else str(max_price)
        return f"price:[{lo}..{hi}],priceCurrency:{self.currency}"

    def search(self, query, limit=50, category_ids=None,
               min_price=None, max_price=None, sort="newlyListed"):
        """Run one Browse API search and return normalized listing dicts."""
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
            "Content-Type": "application/json",
        }
        params = {"q": query, "limit": min(int(limit), 200)}
        if sort:
            params["sort"] = sort
        if category_ids:
            params["category_ids"] = ",".join(str(c) for c in category_ids)
        pf = self._price_filter(min_price, max_price)
        if pf:
            params["filter"] = pf

        resp = requests.get(f"{self.base}/buy/browse/v1/item_summary/search",
                            headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            raise EbayError(
                f"eBay search failed ({resp.status_code}): {resp.text[:300]}"
            )
        payload = resp.json()
        return [self._normalize(it) for it in payload.get("itemSummaries", [])]

    @staticmethod
    def _normalize(it):
        price = it.get("price") or {}
        image = (it.get("image") or {}).get("imageUrl")
        if not image:
            thumbs = it.get("thumbnailImages") or []
            image = thumbs[0].get("imageUrl") if thumbs else None
        seller = it.get("seller") or {}
        loc = it.get("itemLocation") or {}
        shipping = it.get("shippingOptions") or []
        ship_cost = None
        if shipping:
            sc = (shipping[0].get("shippingCost") or {}).get("value")
            ship_cost = float(sc) if sc is not None else None
        return {
            "itemId": it.get("itemId"),
            "title": it.get("title", ""),
            "price": float(price["value"]) if price.get("value") is not None else None,
            "currency": price.get("currency"),
            "shipping": ship_cost,
            "condition": it.get("condition") or "Not specified",
            "conditionId": it.get("conditionId"),
            "url": it.get("itemWebUrl"),
            "image": image,
            "seller": seller.get("username"),
            "feedbackPct": seller.get("feedbackPercentage"),
            "location": loc.get("country"),
            "buyingOptions": it.get("buyingOptions") or [],
        }

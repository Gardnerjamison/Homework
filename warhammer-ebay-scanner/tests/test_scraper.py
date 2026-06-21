"""Tests for the HTML-scraping backend's parser + the full pipeline.

Uses a small fixture that mirrors eBay's `li.s-item` results markup, so we can
validate parsing and filtering without hitting the network.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ebay_scanner.scraper import parse_search_html, _parse_price, _parse_shipping
from ebay_scanner.filters import filter_items

FIXTURE = """
<ul class="srp-results">
  <li class="s-item">
    <a class="s-item__link" href="https://www.ebay.com/itm/shop-on-ebay">
      <div class="s-item__title">Shop on eBay</div></a>
  </li>
  <li class="s-item">
    <a class="s-item__link" href="https://www.ebay.com/itm/123456789012?hash=abc">
      <div class="s-item__title">Warhammer 40k Necron Warriors x10 New in Box Sealed</div></a>
    <span class="s-item__price">$34.99</span>
    <span class="SECONDARY_INFO">Brand New</span>
    <span class="s-item__shipping">Free shipping</span>
    <span class="s-item__location">from United States</span>
    <div class="s-item__image-wrapper"><img src="https://i.ebayimg.com/a.jpg"></div>
  </li>
  <li class="s-item">
    <a class="s-item__link" href="https://www.ebay.com/itm/223456789013">
      <div class="s-item__title">Necron Warriors spare heads x20 bitz lot</div></a>
    <span class="s-item__price">$8.50</span>
    <span class="SECONDARY_INFO">Pre-Owned</span>
    <span class="s-item__shipping">+$4.00 shipping</span>
    <div class="s-item__image-wrapper"><img data-src="https://i.ebayimg.com/b.jpg"></div>
  </li>
  <li class="s-item">
    <a class="s-item__link" href="https://www.ebay.com/itm/323456789014">
      <div class="s-item__title">Necron Lychguard 5 Models Assembled Painted</div></a>
    <span class="s-item__price">$45.00 to $60.00</span>
    <span class="SECONDARY_INFO">Used</span>
  </li>
</ul>
"""


def test_parse_skips_placeholder_and_extracts_fields():
    items = parse_search_html(FIXTURE)
    assert len(items) == 3  # "Shop on eBay" placeholder dropped
    first = items[0]
    assert first["title"].startswith("Warhammer 40k Necron Warriors")
    assert first["price"] == 34.99
    assert first["currency"] == "USD"
    assert first["shipping"] == 0.0
    assert first["condition"] == "Brand New"
    assert first["itemId"] == "123456789012"
    assert first["image"] == "https://i.ebayimg.com/a.jpg"


def test_parse_handles_data_src_and_shipping_cost():
    items = parse_search_html(FIXTURE)
    bits = items[1]
    assert bits["image"] == "https://i.ebayimg.com/b.jpg"  # data-src fallback
    assert bits["shipping"] == 4.0


def test_parse_price_range_takes_first_value():
    val, cur = _parse_price("$45.00 to $60.00")
    assert val == 45.00 and cur == "USD"
    assert _parse_shipping("Free Shipping") == 0.0
    assert _parse_shipping("+£3.99 postage") == 3.99


def test_pipeline_filters_bits_listing():
    items = parse_search_html(FIXTURE)
    kept, dropped = filter_items(items)
    titles = [i["title"] for i in kept]
    assert any("Necron Warriors x10" in t for t in titles)
    assert any("Lychguard" in t for t in titles)
    assert all("bitz" not in t.lower() for t in titles)  # bits listing dropped
    assert len(kept) == 2 and len(dropped) == 1

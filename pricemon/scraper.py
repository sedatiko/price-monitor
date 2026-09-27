"""Fetch product pages and extract name/price/availability via CSS selectors.

Each site is described entirely in the YAML config, so adding a new
competitor never requires a code change - only a new config block.
"""

import re
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

PRICE_RE = re.compile(r"(\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{2})?|\d+)")


@dataclass
class Product:
    site: str
    url: str
    name: str
    price: float | None
    currency: str
    in_stock: bool


def parse_price(text: str) -> float | None:
    """Extract a float from a price string like '£51.77' or '1.299,00 €'."""
    m = PRICE_RE.search(text.replace("\xa0", " "))
    if not m:
        return None
    raw = m.group(1).replace(" ", "")
    # European format: 1.299,00 -> 1299.00
    if "," in raw and (raw.rfind(",") > raw.rfind(".")):
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def extract(html: str, site_cfg: dict, url: str) -> Product:
    """Pull product fields out of a page using the site's CSS selectors."""
    soup = BeautifulSoup(html, "html.parser")
    sel = site_cfg["selectors"]

    name_el = soup.select_one(sel["name"])
    price_el = soup.select_one(sel["price"])

    in_stock = True
    if "availability" in sel:
        avail_el = soup.select_one(sel["availability"])
        avail_text = avail_el.get_text(strip=True).lower() if avail_el else ""
        out_markers = site_cfg.get("out_of_stock_markers", ["out of stock", "unavailable", "sold out"])
        in_stock = bool(avail_text) and not any(m in avail_text for m in out_markers)

    return Product(
        site=site_cfg["name"],
        url=url,
        name=name_el.get_text(strip=True) if name_el else "?",
        price=parse_price(price_el.get_text(strip=True)) if price_el else None,
        currency=site_cfg.get("currency", "USD"),
        in_stock=in_stock,
    )


def fetch(url: str, site_cfg: dict, session: requests.Session | None = None,
          retries: int = 3, backoff: float = 2.0) -> str:
    """GET a page with retries and a polite delay between attempts."""
    sess = session or requests.Session()
    headers = {**DEFAULT_HEADERS, **site_cfg.get("headers", {})}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = sess.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            last_err = e
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url} after {retries} attempts") from last_err


def scrape_site(site_cfg: dict, session: requests.Session | None = None,
                delay: float = 1.5) -> list[Product]:
    """Scrape every configured product URL for one site."""
    products = []
    for url in site_cfg["urls"]:
        html = fetch(url, site_cfg, session=session)
        products.append(extract(html, site_cfg, url))
        time.sleep(delay)
    return products

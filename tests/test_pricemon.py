from pathlib import Path

import pytest

from pricemon import history
from pricemon.report import render
from pricemon.scraper import Product, extract, parse_price

FIXTURES = Path(__file__).parent / "fixtures"

SITE_CFG = {
    "name": "Books to Scrape",
    "currency": "GBP",
    "selectors": {
        "name": ".product_main h1",
        "price": ".product_main .price_color",
        "availability": ".product_main .availability",
    },
    "out_of_stock_markers": ["out of stock"],
}


@pytest.mark.parametrize("text,expected", [
    ("£51.77", 51.77),
    ("$1,299.00", 1299.00),
    ("1.299,00 €", 1299.00),
    ("19", 19.0),
    ("Free", None),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_extract_from_fixture():
    html = (FIXTURES / "product_page.html").read_text()
    p = extract(html, SITE_CFG, "https://x.test/p1")
    assert p.name == "A Light in the Attic"
    assert p.price == 51.77
    assert p.currency == "GBP"
    assert p.in_stock


def test_extract_out_of_stock():
    html = (FIXTURES / "product_page.html").read_text()
    html = html.replace("In stock (22 available)", "Out of stock")
    p = extract(html, SITE_CFG, "https://x.test/p1")
    assert not p.in_stock


def _product(price, in_stock=True, url="https://x.test/p1"):
    return Product(site="S", url=url, name="Widget", price=price,
                   currency="USD", in_stock=in_stock)


def test_history_roundtrip_and_change_detection(tmp_path):
    hist = tmp_path / "history.csv"

    # first run: everything is new
    first = [_product(100.0)]
    changes = history.detect_changes(history.last_snapshot(hist), first)
    assert [c.kind for c in changes] == ["new"]
    history.append(hist, first)

    # second run: price dropped and item went out of stock
    second = [_product(80.0, in_stock=False)]
    changes = history.detect_changes(history.last_snapshot(hist), second)
    kinds = sorted(c.kind for c in changes)
    assert kinds == ["drop", "out_of_stock"]
    drop = next(c for c in changes if c.kind == "drop")
    assert drop.old_price == 100.0
    assert drop.pct == pytest.approx(-20.0)


def test_min_pct_threshold(tmp_path):
    hist = tmp_path / "history.csv"
    history.append(hist, [_product(100.0)])
    changes = history.detect_changes(history.last_snapshot(hist),
                                     [_product(100.5)], min_pct=1.0)
    assert changes == []


def test_report_renders_alerts(tmp_path):
    hist = tmp_path / "history.csv"
    history.append(hist, [_product(100.0)])
    products = [_product(80.0)]
    changes = history.detect_changes(history.last_snapshot(hist), products)
    md = render(products, changes)
    assert "PRICE DROP" in md
    assert "100.00 -> 80.00 USD (-20.0%)" in md
    assert "| S | [Widget](https://x.test/p1) | 80.00 USD | yes |" in md

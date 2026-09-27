"""Append-only price history (CSV) and change detection between runs."""

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .scraper import Product

FIELDS = ["timestamp", "site", "url", "name", "price", "currency", "in_stock"]


@dataclass
class Change:
    product: Product
    old_price: float | None
    kind: str  # "drop" | "rise" | "new" | "back_in_stock" | "out_of_stock"

    @property
    def pct(self) -> float | None:
        if self.old_price and self.product.price:
            return (self.product.price - self.old_price) / self.old_price * 100
        return None


def append(path: Path, products: list[Product]) -> None:
    new_file = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for p in products:
            w.writerow({
                "timestamp": ts, "site": p.site, "url": p.url, "name": p.name,
                "price": p.price, "currency": p.currency, "in_stock": p.in_stock,
            })


def last_snapshot(path: Path) -> dict[str, dict]:
    """Latest recorded row per product URL."""
    if not path.exists():
        return {}
    snap: dict[str, dict] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            snap[row["url"]] = row  # later rows overwrite earlier ones
    return snap


def detect_changes(previous: dict[str, dict], products: list[Product],
                   min_pct: float = 0.0) -> list[Change]:
    """Compare a fresh scrape against the last snapshot."""
    changes = []
    for p in products:
        old = previous.get(p.url)
        if old is None:
            changes.append(Change(p, None, "new"))
            continue
        old_price = float(old["price"]) if old["price"] not in ("", "None") else None
        old_stock = old["in_stock"] == "True"
        if p.in_stock and not old_stock:
            changes.append(Change(p, old_price, "back_in_stock"))
        elif not p.in_stock and old_stock:
            changes.append(Change(p, old_price, "out_of_stock"))
        if p.price is not None and old_price is not None and p.price != old_price:
            pct = abs(p.price - old_price) / old_price * 100
            if pct >= min_pct:
                kind = "drop" if p.price < old_price else "rise"
                changes.append(Change(p, old_price, kind))
    return changes

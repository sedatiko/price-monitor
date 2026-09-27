"""Render scrape results and alerts as Markdown (email/Slack-ready)."""

from datetime import datetime, timezone

from .history import Change
from .scraper import Product

KIND_LABELS = {
    "drop": "PRICE DROP",
    "rise": "PRICE INCREASE",
    "new": "NEW PRODUCT TRACKED",
    "back_in_stock": "BACK IN STOCK",
    "out_of_stock": "OUT OF STOCK",
}


def render(products: list[Product], changes: list[Change]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Price Monitor Report - {now}", ""]

    alerts = [c for c in changes if c.kind != "new"]
    if alerts:
        lines += ["## Alerts", ""]
        for c in alerts:
            p = c.product
            line = f"- **{KIND_LABELS[c.kind]}**: [{p.name}]({p.url}) ({p.site})"
            if c.kind in ("drop", "rise") and c.old_price is not None:
                line += f" {c.old_price:.2f} -> {p.price:.2f} {p.currency} ({c.pct:+.1f}%)"
            lines.append(line)
        lines.append("")
    else:
        lines += ["_No price or stock changes since last run._", ""]

    lines += ["## Current Prices", "", "| Site | Product | Price | In stock |", "|---|---|---|---|"]
    for p in sorted(products, key=lambda x: (x.site, x.name)):
        price = f"{p.price:.2f} {p.currency}" if p.price is not None else "n/a"
        stock = "yes" if p.in_stock else "**no**"
        lines.append(f"| {p.site} | [{p.name}]({p.url}) | {price} | {stock} |")

    return "\n".join(lines) + "\n"

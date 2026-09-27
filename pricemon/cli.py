"""CLI entry point: scrape all configured sites, record history, emit report.

Usage:
    python -m pricemon.cli --config config.yaml
    python -m pricemon.cli --config config.yaml --report-out report.md
"""

import argparse
import sys
from pathlib import Path

import yaml

from . import history, report
from .scraper import scrape_site


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a price monitoring pass.")
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--history", type=Path, default=Path("data/history.csv"))
    ap.add_argument("--report-out", type=Path, help="write Markdown report here (default: stdout)")
    ap.add_argument("--min-change-pct", type=float, default=0.0,
                    help="ignore price moves smaller than this percentage")
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(args.config.read_text())

    products = []
    errors = []
    for site_cfg in cfg["sites"]:
        try:
            products += scrape_site(site_cfg, delay=cfg.get("delay_seconds", 1.5))
        except Exception as e:
            errors.append(f"{site_cfg['name']}: {e}")

    previous = history.last_snapshot(args.history)
    changes = history.detect_changes(previous, products, min_pct=args.min_change_pct)
    history.append(args.history, products)

    md = report.render(products, changes)
    if errors:
        md += "\n## Errors\n\n" + "\n".join(f"- {e}" for e in errors) + "\n"

    if args.report_out:
        args.report_out.write_text(md)
        print(f"report written to {args.report_out}")
    else:
        print(md)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

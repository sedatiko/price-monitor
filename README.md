# Price Monitor — competitor price & stock tracking

Config-driven price monitoring pipeline: point it at competitor product pages,
run it on a schedule, and get a Markdown report (email/Slack-ready) whenever a
price moves or an item goes in/out of stock. Full price history is kept in CSV
for trend analysis.

This is the core deliverable for productized freelance gigs of the form
*"track my competitors' prices and alert me on changes"* — typical market rate
$500–$2,000 for setup plus a monthly monitoring retainer.

## Why it needs no code changes per client

Every target store is described entirely in YAML — URLs, CSS selectors,
currency, out-of-stock markers, optional headers. Onboarding a new client or
competitor means writing a config block, not touching the code.

```yaml
sites:
  - name: Competitor A
    currency: USD
    urls:
      - https://store.example.com/products/widget-pro
    selectors:
      name: "h1.product-title"
      price: "span.price--sale, span.price"
      availability: ".stock-status"
```

## Usage

```bash
pip install -r requirements.txt
python -m pricemon.cli --config config.yaml --history data/history.csv --report-out report.md
```

Schedule with cron for recurring monitoring:

```cron
0 8 * * * cd /opt/price-monitor && python -m pricemon.cli --config config.yaml --report-out report.md
```

Useful flags:

- `--min-change-pct 2.0` — ignore noise; only alert on moves of 2%+ in either direction.
- `--report-out report.md` — write the report to a file instead of stdout.

## Sample alert output

```markdown
# Price Monitor Report - 2026-06-09 21:36 UTC

## Alerts

- **PRICE DROP**: [A Light in the Attic](...) (Demo Store) 51.77 -> 43.99 GBP (-15.0%)

## Current Prices

| Site | Product | Price | In stock |
|---|---|---|---|
| Demo Store | [A Light in the Attic](...) | 43.99 GBP | yes |
```

## Tests

The pipeline is tested offline against HTML fixtures (no network needed):

```bash
python -m pytest tests/
```

## Notes on responsible scraping

- Only target publicly accessible product pages; respect robots.txt and site ToS.
- The scraper uses polite per-request delays (`delay_seconds`) and bounded retries.
- For heavily protected targets (Cloudflare etc.), front requests with a
  scraping API (ScrapingBee, Zyte) by adding its endpoint via per-site config.

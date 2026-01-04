# Real Estate Scout

A Python application to help you find and evaluate potential homes by combining MLS listings with travel time analysis to your important destinations.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (preferred)
# Create .env in repo root with:
# DB_HOST=192.168.1.57
# DB_PORT=5432
# DB_NAME=real_estate_scout
# DB_USER=realestatescoutagent
# DB_PASSWORD=your_password

# Run the tool (default: table output)
python -m etl.main

# Export to CSV
python -m etl.main --output csv --csv-output results.csv
```

## ETL CLI

Run the ETL CLI via:

```bash
python -m etl.main
```

### Flags

```text
--config, -c PATH
    Path to config.yaml file (default: config.yaml)

--output, -o {table,csv,json}
    Output format for search results (default: config value)

--sort-by {price,commute,size,score}
    Sort results by (default: score)

--top N
    Limit output to top N results

--csv-output PATH
    Save CSV output to a file (only used with --output csv)

--max-listings N
    Max listings to process (0 = from config, negative = all)

--all
    Process all listings, ignore config max_listings limit

--no-travel
    Skip OSRM routing and use haversine approximation

--delay SECONDS
    Rate limit delay between travel / geocoding requests

--export {listings,price-history,travel-times,all}
    Export database contents (no new data fetching)

--export-format {csv,json,both}
    Export file format (default: both)

--export-dir DIR
    Directory for export files (default: exports)

--include-inactive
    Include inactive (off-market) listings in export

--stats
    Show database statistics only

--init-db
    Create database tables/indexes if missing

--update-travel
    Recalculate and persist travel times for active listings only (no new HomeHarvest fetch)
```

### Recommended Workflows

```bash
# 1) First run (creates tables + loads market data)
python -m etl.main --init-db

# 2) Quick iteration (small sample + fast travel)
python -m etl.main --max-listings 5 --no-travel

# 3) Normal daily run (respects config.yaml limits)
python -m etl.main

# 4) Recompute commutes only (no listing fetch)
python -m etl.main --update-travel

# 5) Export for spreadsheet / dashboard ingestion
python -m etl.main --export all --export-format both --export-dir exports
```

### Notes

- `--all` overrides your configured listing limit; use it sparingly.
- `--delay` should be `>= 1.0` for OSRM/Nominatim friendliness.
- `--update-travel` requires `database.enabled: true` and only updates existing listings.

## Usage

### Output Formats

```bash
# Table output (default) - displays in terminal
python -m etl.main --output table

# CSV output - prints to stdout
python -m etl.main --output csv

# CSV output - save to file
python -m etl.main --output csv --csv-output results.csv

# JSON output - prints to stdout
python -m etl.main --output json

# JSON output - save to file
python -m etl.main --output json > results.json
```

### Common Options

```bash
# Limit number of listings processed
python -m etl.main --max-listings 10

# Process all listings (ignore config limit)
python -m etl.main --all

# Skip travel API calls (fast, uses haversine approximation)
python -m etl.main --no-travel

# Sort results by: price, commute, size, score
python -m etl.main --sort-by price

# Limit output to top N results
python -m etl.main --top 10

# Set rate limit delay for API calls (seconds)
python -m etl.main --delay 2.0

# Use alternate config file
python -m etl.main --config alt.yaml
```

### Database Export

```bash
# Export all database tables to files
python -m etl.main --export all

# Show database statistics
python -m etl.main --stats
```

### Example Workflows

```bash
# Quick test run (2 listings, no travel API)
python -m etl.main --max-listings 2 --no-travel

# Full run with CSV export
python -m etl.main --all --output csv --csv-output exports/listings.csv

# Top 10 by score as JSON
python -m etl.main --sort-by score --top 10 --output json > top10.json
```

## Web Dashboard

A Next.js web dashboard is available for visualizing listings on a map and exploring data.

```bash
cd web

# Set DATABASE_URL in web/.env.local (create if missing)
# DATABASE_URL=postgresql://user:password@host:5432/real_estate_scout

bun install
bun run dev    # Development server at http://localhost:3000
```

See `web/README.md` for more details.

## Features

- **Fetch listings** from Zillow/Realtor.com using HomeHarvest (free)
- **Calculate travel times** to multiple destinations using OSRM (free)
- **Filter** by price, bedrooms, bathrooms, property type
- **Score and rank** listings based on commute times and value
- **Persist data** to PostgreSQL for historical tracking
- **Track price changes** with automatic price history
- **Output** as table (terminal), CSV, or JSON
- **Property details** including description and features (tags)

## Configuration

Edit `config.yaml` to customize:
- Search location and radius
- Budget constraints
- Destination addresses
- Database connection
- Output preferences

### Environment Variables

For security, you can override database settings with environment variables (preferred):
- `DB_HOST` - Database host
- `DB_PORT` - Database port
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password

Recommended: create a `.env` in the repo root for Python, and a `web/.env.local` for the web dashboard.

## Requirements

All dependencies are free:
- homeharvest (Zillow/Realtor.com data)
- OSRM public API (travel times)
- Nominatim (geocoding)
- PostgreSQL (data persistence)
- pandas, pyyaml, rich, haversine

## License

MIT

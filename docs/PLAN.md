# HomeHelper - Real Estate Decision Tool

A Python application to help you find and evaluate potential homes by combining MLS listings with travel time analysis to your important destinations.

## Overview

HomeHelper fetches current real estate listings from Zillow (via HomeHarvest), calculates travel times to your specified destinations (via free OpenRouteService API), and generates well-formatted reports to help you make informed home-buying decisions.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your preferences in config.yaml

# Run the tool
python -m src.main --output table

# Export to CSV
python -m src.main --output csv -o outputs/listings.csv
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  HomeHarvest    │────▶│   Nominatim     │────▶│  OpenRouteService│
│  (Zillow Data)  │     │  (Geocoding)    │     │  (Distance)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Output Formatter│
                                               │  (Table/CSV/JSON)│
                                               └─────────────────┘
```

## Data Flow

1. **Load Configuration** - Read `config.yaml` for search params, budget, destinations
2. **Fetch Listings** - HomeHarvest searches Zillow by location + radius
3. **Filter Results** - Apply price range, bedrooms, property type filters
4. **Geocode** - Nominatim converts addresses to coordinates (fallback)
5. **Calculate Travel** - OpenRouteService gets travel times to 4 destinations
6. **Score & Rank** - Optional scoring algorithm for comparison
7. **Generate Output** - Table, CSV, or JSON format

## Dependencies (All Free)

| Package | Purpose | Free Tier |
|---------|---------|-----------|
| homeharvest | MLS listing data from Zillow | Unlimited |
| openrouteservice | Distance matrix & routing | 2,000 req/day |
| pyyaml | Configuration parsing | Unlimited |
| pandas | Data manipulation | Unlimited |
| rich | Terminal table display | Unlimited |
| python-dotenv | Environment variables | Unlimited |

**Total Cost: $0/month**

## Configuration

### `config.yaml`

```yaml
# Search Parameters
search:
  center_address: "1490 Tuskawilla Rd, Oviedo, FL 32765"
  radius_miles: 20
  listing_type: for_sale
  property_types:
    - single_family
  past_days: 120

# Budget Constraints
budget:
  min_price: 500000
  max_price: 850000
  min_bedrooms: 3
  min_bathrooms: 2

# Destinations for travel time calculation
destinations:
  - name: "Animal Hospital"
    address: "1490 Tuskawilla Rd, Oviedo, FL 32765"
  - name: "Airport"
    address: "1 Jeff Fuqua Blvd, Orlando, FL 32827"
  - name: "Epcot"
    address: "Epcot, Bay Lake, FL"
  - name: "Universal"
    address: "6601 Adventure Wy, Orlando, FL 32819"

# Travel Preferences
travel:
  mode: driving

# Output Settings
output:
  default_format: table
  include_scores: true
```

## Major Design Decisions

### Why HomeHarvest for Listings?

- **Free**: No API costs
- **Flexible**: Supports ZIP, city, address, neighborhood searches
- **Structured**: Returns pandas DataFrame, pydantic models, or raw JSON
- **Maintained**: Active project with regular updates

**Alternative Considered**: Zillow's deprecated official API (no longer functional)

### Why OpenRouteService for Travel Times?

| Feature | Google Maps | OpenRouteService |
|---------|-------------|------------------|
| Credit Card Required | Yes | No |
| Cost | ~$10-50/month | $0 |
| Accuracy | Excellent | Very Good |
| Free Requests | N/A | 2,000/day |

**Decision**: OpenRouteService chosen for zero cost while maintaining sufficient accuracy for home-buying decisions.

### Why Nominatim for Geocoding?

- Free via OpenStreetMap
- Used only as fallback (HomeHarvest usually provides coordinates)
- Rate-limited to 1 req/second (handled in code)

### Output Formats

| Format | Use Case |
|--------|----------|
| Table | Quick terminal review with sorting |
| CSV | Spreadsheet analysis, external tools |
| JSON | Programmatic integration, APIs |

### Scoring Algorithm (Optional)

```
combined_score = (travel_score * 0.5) + (price_score * 0.3) + (size_score * 0.2)

Where:
- travel_score = inverse of average travel time (lower = better)
- price_score = inverse of price within budget range
- size_score = normalized bedrooms + bathrooms + sqft
```

Weights can be adjusted in future versions via config.

## API Rate Limits & Safety

| API | Free Limit | Our Usage | Safety Margin |
|-----|-----------|-----------|---------------|
| HomeHarvest | Unlimited | ~1 search/run | N/A |
| OSRM | 1 req/second | ~8-40 req/run (configurable) | Rate-limited in code |
| Nominatim | 1 req/second | ~4 geocodes (destinations only) | Rate-limited in code |

**OSRM Rate Limiting**: The public OSRM demo server requires max 1 request/second. Default delay is 1.1 seconds.

## Configuration

### `config.yaml`

```yaml
# Search Parameters
search:
  center_address: "1490 Tuskawilla Rd, Oviedo, FL 32765"
  radius_miles: 20
  listing_type: for_sale
  property_types:
    - single_family
  past_days: 120

# Budget Constraints
budget:
  min_price: 500000
  max_price: 850000
  min_bedrooms: 3
  min_bathrooms: 2

# Destinations for travel time calculation
destinations:
  - name: "Animal Hospital"
    address: "1490 Tuskawilla Rd, Oviedo, FL 32765"
  - name: "Airport"
    address: "1 Jeff Fuqua Blvd, Orlando, FL 32827"
  - name: "Epcot"
    address: "Epcot, Bay Lake, FL"
  - name: "Universal"
    address: "6601 Adventure Wy, Orlando, FL 32819"

# Output Settings
output:
  default_format: table
  include_scores: true

# Request Limits (for faster iteration)
limits:
  max_listings: 2        # Process only top N listings (0 = all). Set to 2 for quick testing.
  skip_travel_calculation: false  # true = skip OSRM, use haversine only
  max_destinations: 4    # Limit destinations to calculate (0 = all)

# OSRM Settings (free public demo server)
osrm:
  use_approximate: false  # true = haversine only, false = full OSRM routing
  rate_limit_delay: 1.1   # seconds between requests (OSRM requires 1.0+)
```

### CLI Overrides

```bash
# Process all listings (ignore max_listings)
python -m src.main --all

# Skip travel calculations (fast, use haversine)
python -m src.main --no-travel

# Custom max listings
python -m src.main --max-listings 10

# Custom rate limit delay
python -m src.main --delay 2.0
```

### Performance Examples

| Mode | Listings | Requests | Time |
|------|----------|----------|------|
| Quick test (config default) | 2 | 8 | ~10 sec |
| Normal | 20 | 80 | ~90 sec |
| Full | 51 | 204 | ~4 min |
| No travel | any | 0 | ~5 sec |

## Project Structure

```
home_helper/
├── config.yaml                 # User configuration
├── requirements.txt            # Dependencies
├── README.md                   # Quick start guide
├── PLAN.md                     # This document
├── docs/                       # Documentation
│   └── PLAN.md                 # Detailed planning document
├── src/
│   ├── __init__.py
│   ├── main.py                 # CLI entry point
│   ├── config.py               # Config loader
│   ├── search.py               # HomeHarvest integration
│   ├── travel.py               # OpenRouteService integration
│   ├── geocode.py              # Nominatim geocoding (fallback)
│   ├── models.py               # Data models
│   ├── formatter.py            # Output formatters
│   └── filter.py               # Listing filters
└── outputs/                    # Generated reports
```

## Usage Examples

```bash
# Default: table output sorted by combined score
python -m src.main

# CSV export
python -m src.main --output csv -o outputs/listings.csv

# Filter and sort
python -m src.main --filter "bedrooms>=4" --sort-by price

# Top 10 results
python -m src.main --top 10 --output table

# JSON for programmatic use
python -m src.main --output json > results.json
```

## Data Models

### Listing

| Field | Type | Description |
|-------|------|-------------|
| address | str | Full property address |
| price | int | Listing price |
| bedrooms | int | Number of bedrooms |
| bathrooms | float | Number of bathrooms |
| sqft | int | Living area square footage |
| zestimate | Optional[int] | Zillow estimate |
| listing_url | str | Link to listing |
| lat | float | Latitude |
| lng | float | Longitude |
| travel_times | Dict[str, TravelResult] | Travel data to each destination |
| combined_score | Optional[float] | Ranking score |

### TravelResult

| Field | Type | Description |
|-------|------|-------------|
| destination | str | Destination name |
| duration_minutes | int | Travel time in minutes |
| distance_miles | float | Distance in miles |
| traffic_aware | bool | Whether traffic was considered |

## Error Handling Strategy

| Scenario | Fallback Behavior |
|----------|------------------|
| OpenRouteService unavailable | Use Haversine straight-line distance |
| Missing coordinates | Geocode via Nominatim |
| Nominatim rate-limited | Skip travel time for that listing |
| HomeHarvest blocked | Use cached data if available |
| Missing listing fields | Filter out or mark as N/A |

## Future Enhancements

1. **Interactive Map**: Generate Folium map with all listings and travel radii
2. **Multiple Scores**: Allow configurable weighting (e.g., prioritize commute)
3. **Historical Prices**: Track price changes over time
4. **School Ratings**: Integrate school district data
5. **Notifications**: Email/SMS alerts for new listings matching criteria
6. **Web Interface**: Simple Flask/Streamlit UI
7. **Multiple Center Points**: Search across multiple locations

## License

MIT License - Free for personal use.

## Credits

- [HomeHarvest](https://github.com/ZacharyHampton/HomeHarvest) - Zillow listing data
- [OpenRouteService](https://openrouteservice.org/) - Free routing API
- [Nominatim](https://nominatim.openstreetmap.org/) - Free geocoding

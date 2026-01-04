"""Configuration loader for Real Estate Scout."""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from .models import Config, DatabaseConfig


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file with environment overrides."""
    load_dotenv()

    if config_path is None:
        config_path = os.getenv("HOMEBASE_CONFIG_PATH", "config.yaml")

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r") as f:
        data = yaml.safe_load(f)

    search = data.get("search", {})
    budget = data.get("budget", {})
    destinations = data.get("destinations", [])
    travel = data.get("travel", {})
    output = data.get("output", {})
    limits = data.get("limits", {})
    osrm = data.get("osrm", {})
    db_data = data.get("database", {})
    freshness = data.get("freshness", {})

    # Build database config with environment variable overrides
    database = DatabaseConfig(
        host=os.getenv("DB_HOST", db_data.get("host", "localhost")),
        port=int(os.getenv("DB_PORT", db_data.get("port", 5432))),
        name=os.getenv("DB_NAME", db_data.get("name", "real_estate_scout")),
        user=os.getenv("DB_USER", db_data.get("user", "")),
        password=os.getenv("DB_PASSWORD", db_data.get("password", "")),
        enabled=db_data.get("enabled", False),
    )

    return Config(
        center_address=search.get("center_address", ""),
        radius_miles=search.get("radius_miles", 20),
        listing_type=search.get("listing_type", "for_sale"),
        property_types=search.get("property_types", ["single_family"]),
        past_days=search.get("past_days", 120),
        min_price=budget.get("min_price", 0),
        max_price=budget.get("max_price", 10000000),
        min_bedrooms=budget.get("min_bedrooms", 0),
        min_bathrooms=budget.get("min_bathrooms", 0),
        destinations=destinations,
        travel_mode=travel.get("mode", "driving"),
        output_format=output.get("default_format", "table"),
        include_scores=output.get("include_scores", True),
        max_listings=limits.get("max_listings", 0),
        skip_travel=limits.get("skip_travel_calculation", False),
        max_destinations=limits.get("max_destinations", 0),
        use_approximate=osrm.get("use_approximate", False),
        rate_limit_delay=osrm.get("rate_limit_delay", 1.1),
        database=database,
        listing_max_age_days=freshness.get("listing_max_age_days", 7),
    )

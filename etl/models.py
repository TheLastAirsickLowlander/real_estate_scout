"""Data models for Real Estate Scout."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List


@dataclass
class DatabaseConfig:
    """Database connection configuration."""

    host: str = "localhost"
    port: int = 5432
    name: str = "real_estate_scout"
    user: str = ""
    password: str = ""
    enabled: bool = False


@dataclass
class TravelResult:
    """Travel time result for a single destination."""

    destination: str
    duration_minutes: int
    distance_miles: float
    traffic_aware: bool = False


@dataclass
class Listing:
    """Real estate listing with travel times."""

    address: str
    price: int
    bedrooms: int
    bathrooms: float
    sqft: int
    zestimate: Optional[int] = None
    listing_url: str = ""
    zillow_url: str = ""
    status: str = ""  # HomeHarvest `status` (e.g. FOR_SALE)
    mls_status: str = ""  # HomeHarvest `mls_status` (e.g. Active)
    lat: float = 0.0
    lng: float = 0.0
    travel_times: Dict[str, TravelResult] = field(default_factory=dict)
    combined_score: Optional[float] = None
    description: str = ""
    highlights: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    # Database tracking fields
    id: Optional[int] = None
    first_seen: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def to_dict(self, include_features: bool = False) -> dict:
        """Convert listing to dictionary for CSV/JSON export.

        Args:
            include_features: If True, include features array (for JSON export).
                             If False, exclude features (for CSV export).
        """
        result = {
            "address": self.address,
            "price": self.price,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "sqft": self.sqft,
            "zestimate": self.zestimate,
            "url": self.listing_url,
            "zillow_url": self.zillow_url,
            "status": self.status,
            "mls_status": self.mls_status,
            "score": self.combined_score,
            "description": self.description,
            "highlights": self.highlights,
        }
        for dest, travel in self.travel_times.items():
            result[f"commute_{dest}"] = travel.duration_minutes
            result[f"distance_{dest}"] = travel.distance_miles
        if include_features:
            result["features"] = self.features
            result["highlights"] = self.highlights
        return result


@dataclass
class Config:
    """Application configuration."""

    center_address: str
    radius_miles: int
    listing_type: str
    property_types: List[str]
    past_days: int
    min_price: int
    max_price: int
    min_bedrooms: int
    min_bathrooms: int
    destinations: List[Dict[str, str]]
    travel_mode: str
    output_format: str
    include_scores: bool
    max_listings: int = 0
    skip_travel: bool = False
    max_destinations: int = 0
    use_approximate: bool = False
    rate_limit_delay: float = 1.1
    # Database configuration
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    # Data freshness
    listing_max_age_days: int = 7

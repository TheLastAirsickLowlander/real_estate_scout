"""Fetch listings using HomeHarvest library."""

import re
from typing import List, Optional
from urllib.parse import quote

import homeharvest

from .highlights import distill_highlights
from .models import Listing


def _build_zillow_url(address: str) -> str:
    """Build a Zillow search URL from a listing address.

    This does not guarantee an exact 1:1 match to a specific Zillow listing.
    Zillow will usually resolve this to either the property detail page or a
    filtered search results page.
    """

    normalized = address.strip().lower()
    normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")

    if not normalized:
        return ""

    slug = quote(normalized, safe="-")
    return f"https://www.zillow.com/homes/{slug}_rb/"


class ListingFetcher:
    """Fetch real estate listings from Realtor.com via HomeHarvest."""

    def __init__(self):
        """Initialize the fetcher."""

    def search(
        self,
        location: str,
        radius_miles: float = 20,
        listing_type: str = "for_sale",
        property_types: Optional[List[str]] = None,
        past_days: int = 120,
        price_min: int = 0,
        price_max: int = 10000000,
        beds_min: int = 0,
        baths_min: float = 0,
    ) -> List[Listing]:
        """Search for listings around a location."""
        try:
            properties = homeharvest.scrape_property(
                location=location,
                listing_type=listing_type,
                property_type=property_types,
                radius=radius_miles,
                past_days=past_days,
                price_min=price_min,
                price_max=price_max,
                beds_min=beds_min,
                baths_min=baths_min,
                return_type="pydantic",
                extra_property_data=True,
            )

            return self._convert_to_app_listings(list(properties))  # type: ignore[arg-type]

        except Exception as exc:
            # Preserve current behavior (best-effort scraping)
            print(f"Error fetching listings: {exc}")
            import traceback

            traceback.print_exc()
            return []

    def _convert_to_app_listings(self, properties: list) -> List[Listing]:
        """Convert HomeHarvest Property objects to app Listing models."""
        if not properties:
            return []

        listings: list[Listing] = []
        for prop in properties:
            address = str(getattr(prop.address, "full_line", ""))
            if prop.address:
                city = getattr(prop.address, "city", "")
                state = getattr(prop.address, "state", "")
                zip_code = getattr(prop.address, "zip_code", "")
                if city or state or zip_code:
                    address = f"{address}, {city}, {state} {zip_code}".strip(", ")

            price = int(prop.list_price) if prop.list_price else 0
            beds = (
                int(prop.description.beds)
                if prop.description and prop.description.beds
                else 0
            )
            full_baths = (
                int(prop.description.baths_full)
                if prop.description and prop.description.baths_full
                else 0
            )
            half_baths = (
                int(prop.description.baths_half)
                if prop.description and prop.description.baths_half
                else 0
            )
            bathrooms = full_baths + (half_baths * 0.5)
            sqft = (
                int(prop.description.sqft)
                if prop.description and prop.description.sqft
                else 0
            )
            lat = float(prop.latitude) if prop.latitude else 0.0
            lng = float(prop.longitude) if prop.longitude else 0.0

            description = (
                str(prop.description.text)
                if prop.description and prop.description.text
                else ""
            )

            highlight_result = distill_highlights(description)

            features = list(prop.tags) if prop.tags else []
            features = [tag.replace("_", " ").title() for tag in features]

            listing_url = str(prop.property_url) if prop.property_url else ""

            listings.append(
                Listing(
                    address=address,
                    price=price,
                    bedrooms=beds,
                    bathrooms=bathrooms,
                    sqft=sqft,
                    zestimate=int(prop.estimated_value)
                    if prop.estimated_value
                    else None,
                    listing_url=listing_url,
                    zillow_url=_build_zillow_url(address),
                    status=str(getattr(prop, "status", "") or ""),
                    mls_status=str(getattr(prop, "mls_status", "") or ""),
                    lat=lat,
                    lng=lng,
                    description=description,
                    highlights=highlight_result.highlights,
                    features=features,
                )
            )

        return listings

"""Travel time calculation using OSRM public demo (free, no API key)."""

import json
import time
from typing import Dict, List, Optional

import requests
from haversine import haversine, Unit

from .models import Listing, TravelResult


class TravelCalculator:
    """Calculate travel times using OSRM public demo server."""

    OSRM_BASE_URL = "https://router.project-osrm.org"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self, use_approximate: bool = False, rate_limit_delay: float = 1.1):
        """Initialize travel calculator.

        Args:
            use_approximate: If True, skip OSRM and use haversine approximation
            rate_limit_delay: Seconds between API requests (OSRM requires 1.0+)
        """
        self._dest_cache = {}
        self.use_approximate = use_approximate
        self.rate_limit_delay = rate_limit_delay

    def calculate_matrix(
        self, listings: List[Listing], destinations: List[Dict[str, str]]
    ) -> Dict[str, Dict[str, TravelResult]]:
        """Calculate travel times from each listing to all destinations."""
        if not listings or not destinations:
            return {}

        all_results = {}

        dest_coords = []
        for dest in destinations:
            coords = self._get_destination_coords(dest["address"])
            dest_coords.append((dest["name"], coords))

        for i, listing in enumerate(listings):
            if not listing.lat or not listing.lng:
                all_results[listing.address] = {}
                continue

            listing_results = {}

            for dest_name, dest_coord in dest_coords:
                result = self._calculate_route(
                    (listing.lat, listing.lng), dest_coord, dest_name
                )
                if result:
                    listing_results[dest_name] = result

            all_results[listing.address] = listing_results

            progress = min(i + 1, len(listings))
            if progress % 10 == 0:
                print(
                    f"  Calculated travel times for {progress}/{len(listings)} listings..."
                )

            time.sleep(self.rate_limit_delay)

        return all_results

    def _calculate_route(
        self, origin: tuple, dest: tuple, dest_name: str
    ) -> Optional[TravelResult]:
        """Calculate route using OSRM or haversine approximation."""
        if self.use_approximate:
            return self._haversine_fallback(origin, dest, dest_name)

        try:
            url = f"{self.OSRM_BASE_URL}/route/v1/driving/{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
            params = {"overview": "false", "alternatives": "false"}

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                duration_sec = route.get("duration", 0)
                distance_m = route.get("distance", 0)

                duration_min = int(duration_sec / 60) if duration_sec else 0
                distance_mi = round(distance_m / 1609.34, 1) if distance_m else 0

                return TravelResult(
                    destination=dest_name,
                    duration_minutes=duration_min,
                    distance_miles=distance_mi,
                    traffic_aware=False,
                )

        except (
            requests.RequestException,
            json.JSONDecodeError,
            KeyError,
            IndexError,
        ):
            pass

        return self._haversine_fallback(origin, dest, dest_name)

    def _haversine_fallback(
        self, origin: tuple, dest: tuple, dest_name: str
    ) -> TravelResult:
        """Calculate straight-line distance using haversine formula."""
        distance_km = haversine(origin, dest, unit=Unit.KILOMETERS)
        distance_mi = round(distance_km * 0.621371, 1)

        driving_distance = distance_mi * 1.4
        duration_min = int(driving_distance * 2)

        return TravelResult(
            destination=dest_name,
            duration_minutes=duration_min,
            distance_miles=distance_mi,
            traffic_aware=False,
        )

    def _get_destination_coords(self, address: str) -> tuple:
        """Get coordinates for a destination with caching."""
        if address in self._dest_cache:
            return self._dest_cache[address]

        coords = self._geocode_address(address)
        self._dest_cache[address] = coords
        return coords

    def _geocode_address(self, address: str) -> tuple:
        """Geocode address using Nominatim (free, rate-limited)."""
        try:
            url = self.NOMINATIM_URL
            params = {"q": address, "format": "json", "limit": 1}
            headers = {"User-Agent": "HomeHelper/1.0"}

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])

        except (requests.RequestException, json.JSONDecodeError, IndexError, KeyError):
            pass

        return 28.5, -81.0

    def calculate_single(
        self, listing: Listing, dest_address: str, dest_name: str
    ) -> Optional[TravelResult]:
        """Calculate travel time for single listing-destination pair."""
        if not listing.lat or not listing.lng:
            return None

        dest_coord = self._get_destination_coords(dest_address)
        time.sleep(self.rate_limit_delay)
        return self._calculate_route((listing.lat, listing.lng), dest_coord, dest_name)

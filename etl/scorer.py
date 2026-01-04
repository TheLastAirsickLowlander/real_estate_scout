"""Scoring algorithm for ranking listings."""

from typing import List

from .models import Listing


class ListingScorer:
    """Score and rank listings based on multiple factors."""

    def __init__(
        self,
        travel_weight: float = 0.5,
        price_weight: float = 0.3,
        size_weight: float = 0.2,
        max_budget: int = 850000,
        min_budget: int = 500000,
    ):
        self.travel_weight = travel_weight
        self.price_weight = price_weight
        self.size_weight = size_weight
        self.max_budget = max_budget
        self.min_budget = min_budget

    def score_listings(self, listings: List[Listing]) -> List[Listing]:
        """Score all listings and return sorted by score."""
        max_travel = self._max_commute(listings)
        max_price = self.max_budget
        max_size = self._max_sqft(listings)

        for listing in listings:
            listing.combined_score = self._calculate_score(
                listing, max_travel, max_price, max_size
            )

        valid_listings = [l for l in listings if l.combined_score is not None]
        valid_listings.sort(key=lambda x: x.combined_score or 0, reverse=True)
        return valid_listings

    def _calculate_score(
        self, listing: Listing, max_travel: int, max_price: int, max_size: int
    ) -> float:
        """Calculate combined score for a listing."""
        travel_score = self._travel_score(listing, max_travel)
        price_score = self._price_score(listing.price)
        size_score = self._size_score(listing, max_size)

        return (
            travel_score * self.travel_weight
            + price_score * self.price_weight
            + size_score * self.size_weight
        )

    def _travel_score(self, listing: Listing, max_travel: int) -> float:
        """Score based on average commute time (lower = better)."""
        if not listing.travel_times:
            return 0.0

        avg_minutes = self._avg_commute(listing)
        if avg_minutes == 0 or max_travel == 0:
            return 1.0

        normalized = 1 - (avg_minutes / max_travel)
        return max(0.0, normalized)

    def _price_score(self, price: int) -> float:
        """Score based on price within budget (lower = better)."""
        if price <= self.min_budget:
            return 1.0

        if price >= self.max_budget:
            return 0.0

        budget_range = self.max_budget - self.min_budget
        price_over_min = price - self.min_budget
        return 1 - (price_over_min / budget_range)

    def _size_score(self, listing: Listing, max_size: int) -> float:
        """Score based on property size."""
        if max_size == 0:
            return 0.5

        score = listing.sqft / max_size
        score += listing.bedrooms / 6
        score += listing.bathrooms / 4
        return min(1.0, score / 3)

    def _avg_commute(self, listing: Listing) -> float:
        """Calculate average commute in minutes."""
        if not listing.travel_times:
            return 0

        times = [
            t.duration_minutes
            for t in listing.travel_times.values()
            if t.duration_minutes > 0
        ]
        if not times:
            return 0

        return sum(times) / len(times)

    def _max_commute(self, listings: List[Listing]) -> int:
        """Get maximum average commute across all listings."""
        max_avg = 0
        for listing in listings:
            avg = self._avg_commute(listing)
            if avg > max_avg:
                max_avg = avg
        return max(60, max_avg)

    def _max_sqft(self, listings: List[Listing]) -> int:
        """Get maximum sqft across all listings."""
        max_sqft = 0
        for listing in listings:
            if listing.sqft > max_sqft:
                max_sqft = listing.sqft
        return max(2000, max_sqft)

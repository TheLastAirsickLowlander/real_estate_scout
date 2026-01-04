"""Filter listings based on configuration criteria."""

from typing import List, Optional

import pandas as pd

from .models import Listing


class ListingFilter:
    """Filter listings by various criteria."""

    def __init__(
        self,
        min_price: int = 0,
        max_price: int = 10000000,
        min_bedrooms: int = 0,
        min_bathrooms: int = 0,
        property_types: Optional[List[str]] = None,
    ):
        self.min_price = min_price
        self.max_price = max_price
        self.min_bedrooms = min_bedrooms
        self.min_bathrooms = min_bathrooms
        self.property_types = property_types or []

    def filter_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter a pandas DataFrame of listings."""
        if df.empty:
            return df

        result = df.copy()

        if "price" in result.columns:
            mask = (result["price"] >= self.min_price) & (
                result["price"] <= self.max_price
            )
            result = result[mask]

        if "bedrooms" in result.columns:
            result = result[result["bedrooms"] >= self.min_bedrooms]

        if "bathrooms" in result.columns:
            result = result[result["bathrooms"] >= self.min_bathrooms]

        if "property_type" in result.columns and self.property_types:
            mask = result["property_type"].isin(self.property_types)
            result = result[mask]

        return result

    def filter_listings(self, listings: List[Listing]) -> List[Listing]:
        """Filter a list of Listing objects."""
        return [
            l
            for l in listings
            if self.min_price <= l.price <= self.max_price
            and l.bedrooms >= self.min_bedrooms
            and l.bathrooms >= self.min_bathrooms
        ]

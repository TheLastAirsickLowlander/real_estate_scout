"""Export database contents to CSV and JSON files."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from .database import ListingDatabase

logger = logging.getLogger(__name__)


class DataExporter:
    """Export database data to CSV and JSON formats."""

    def __init__(self, db: ListingDatabase, output_dir: Path | str = "exports"):
        """Initialize the exporter.

        Args:
            db: Database instance to export from.
            output_dir: Directory to write export files to.
        """
        self.db = db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_timestamp(self) -> str:
        """Get a timestamp string for filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def export_listings_csv(
        self, include_inactive: bool = False, filename: str | None = None
    ) -> Path:
        """Export listings to CSV file.

        Args:
            include_inactive: Include inactive listings.
            filename: Custom filename (without extension).

        Returns:
            Path to the created file.
        """
        data = self.db.export_all_listings(include_inactive)

        if not data:
            logger.warning("No listings to export")
            return Path()

        if filename is None:
            filename = f"listings_{self._get_timestamp()}"

        filepath = self.output_dir / f"{filename}.csv"

        # Flatten features list to comma-separated string for CSV
        for row in data:
            if isinstance(row.get("features"), list):
                row["features"] = ", ".join(row["features"])

        fieldnames = list(data[0].keys())

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Exported {len(data)} listings to {filepath}")
        return filepath

    def export_listings_json(
        self,
        include_inactive: bool = False,
        include_travel: bool = True,
        filename: str | None = None,
    ) -> Path:
        """Export listings to JSON file.

        Args:
            include_inactive: Include inactive listings.
            include_travel: Include nested travel times.
            filename: Custom filename (without extension).

        Returns:
            Path to the created file.
        """
        if include_travel:
            data = self.db.export_listings_with_travel(include_inactive)
        else:
            data = self.db.export_all_listings(include_inactive)

        if not data:
            logger.warning("No listings to export")
            return Path()

        if filename is None:
            filename = f"listings_{self._get_timestamp()}"

        filepath = self.output_dir / f"{filename}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Exported {len(data)} listings to {filepath}")
        return filepath

    def export_price_history_csv(self, filename: str | None = None) -> Path:
        """Export price history to CSV file.

        Args:
            filename: Custom filename (without extension).

        Returns:
            Path to the created file.
        """
        data = self.db.export_price_history()

        if not data:
            logger.warning("No price history to export")
            return Path()

        if filename is None:
            filename = f"price_history_{self._get_timestamp()}"

        filepath = self.output_dir / f"{filename}.csv"

        fieldnames = list(data[0].keys())

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Exported {len(data)} price history records to {filepath}")
        return filepath

    def export_price_history_json(self, filename: str | None = None) -> Path:
        """Export price history to JSON file.

        Args:
            filename: Custom filename (without extension).

        Returns:
            Path to the created file.
        """
        data = self.db.export_price_history()

        if not data:
            logger.warning("No price history to export")
            return Path()

        if filename is None:
            filename = f"price_history_{self._get_timestamp()}"

        filepath = self.output_dir / f"{filename}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Exported {len(data)} price history records to {filepath}")
        return filepath

    def export_travel_times_csv(self, filename: str | None = None) -> Path:
        """Export travel times to CSV file.

        Args:
            filename: Custom filename (without extension).

        Returns:
            Path to the created file.
        """
        data = self.db.export_travel_times()

        if not data:
            logger.warning("No travel times to export")
            return Path()

        if filename is None:
            filename = f"travel_times_{self._get_timestamp()}"

        filepath = self.output_dir / f"{filename}.csv"

        fieldnames = list(data[0].keys())

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Exported {len(data)} travel time records to {filepath}")
        return filepath

    def export_travel_times_json(self, filename: str | None = None) -> Path:
        """Export travel times to JSON file.

        Args:
            filename: Custom filename (without extension).

        Returns:
            Path to the created file.
        """
        data = self.db.export_travel_times()

        if not data:
            logger.warning("No travel times to export")
            return Path()

        if filename is None:
            filename = f"travel_times_{self._get_timestamp()}"

        filepath = self.output_dir / f"{filename}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Exported {len(data)} travel time records to {filepath}")
        return filepath

    def export_all(
        self,
        format: str = "both",
        include_inactive: bool = False,
    ) -> dict[str, list[Path]]:
        """Export all data tables.

        Args:
            format: Export format - 'csv', 'json', or 'both'.
            include_inactive: Include inactive listings.

        Returns:
            Dict mapping table names to list of created file paths.
        """
        timestamp = self._get_timestamp()
        results: dict[str, list[Path]] = {
            "listings": [],
            "price_history": [],
            "travel_times": [],
        }

        if format in ("csv", "both"):
            results["listings"].append(
                self.export_listings_csv(include_inactive, f"listings_{timestamp}")
            )
            results["price_history"].append(
                self.export_price_history_csv(f"price_history_{timestamp}")
            )
            results["travel_times"].append(
                self.export_travel_times_csv(f"travel_times_{timestamp}")
            )

        if format in ("json", "both"):
            results["listings"].append(
                self.export_listings_json(
                    include_inactive,
                    include_travel=True,
                    filename=f"listings_{timestamp}",
                )
            )
            results["price_history"].append(
                self.export_price_history_json(f"price_history_{timestamp}")
            )
            results["travel_times"].append(
                self.export_travel_times_json(f"travel_times_{timestamp}")
            )

        return results

    def print_stats(self) -> None:
        """Print database statistics to stdout."""
        stats = self.db.get_database_stats()

        print("\nDatabase Statistics")
        print("=" * 40)
        print(f"Active listings:      {stats['active_listings']:,}")
        print(f"Inactive listings:    {stats['inactive_listings']:,}")
        print(f"Price history records:{stats['price_history_records']:,}")
        print(f"Travel time records:  {stats['travel_time_records']:,}")
        print(f"Unique destinations:  {stats['unique_destinations']:,}")
        print(f"Listings with drops:  {stats['listings_with_price_drops']:,}")
        print("=" * 40)

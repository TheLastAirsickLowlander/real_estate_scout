"""Export-related CLI command."""

from __future__ import annotations

import argparse

from ..db import ListingDatabase
from ..exporter import DataExporter


def run_export(args: argparse.Namespace, db: ListingDatabase) -> None:
    exporter = DataExporter(db, args.export_dir)

    exporter.print_stats()

    export_type = args.export
    export_format = args.export_format
    include_inactive = args.include_inactive

    print(f"\nExporting {export_type} as {export_format}...")
    print(f"Output directory: {args.export_dir}")

    if export_type == "all":
        results = exporter.export_all(export_format, include_inactive)
        print("\nExported files:")
        for table, paths in results.items():
            for path in paths:
                if path:
                    print(f"  {path}")
    elif export_type == "listings":
        if export_format in ("csv", "both"):
            path = exporter.export_listings_csv(include_inactive)
            print(f"  {path}")
        if export_format in ("json", "both"):
            path = exporter.export_listings_json(include_inactive, include_travel=True)
            print(f"  {path}")
    elif export_type == "price-history":
        if export_format in ("csv", "both"):
            path = exporter.export_price_history_csv()
            print(f"  {path}")
        if export_format in ("json", "both"):
            path = exporter.export_price_history_json()
            print(f"  {path}")
    elif export_type == "travel-times":
        if export_format in ("csv", "both"):
            path = exporter.export_travel_times_csv()
            print(f"  {path}")
        if export_format in ("json", "both"):
            path = exporter.export_travel_times_json()
            print(f"  {path}")

    print("\nExport complete!")

"""Backwards-compatible import wrapper.

The ETL database layer was split into `etl.db.*` modules. This file remains as a
shim so existing imports (`from etl.database import ListingDatabase`) keep
working.
"""

from .db.client import ListingDatabase

__all__ = ["ListingDatabase"]

#!/usr/bin/env python3
"""Update highlights for existing listings by re-processing descriptions."""

import psycopg2
from highlights import distill_highlights
import json

# Database connection
conn = psycopg2.connect(
    "postgresql://realestatescoutagent:password123@192.168.1.57:5432/real_estate_scout"
)


def format_highlight(highlight: str) -> str:
    """Format highlight as +positive or -negative."""
    caution_keywords = [
        "verify",
        "marketing",
        "check",
        "ask",
        "flood",
        "short-term",
        "risk",
    ]
    if any(keyword in highlight.lower() for keyword in caution_keywords):
        return "- " + highlight
    else:
        return "+ " + highlight


with conn.cursor() as cur:
    # Select listings with descriptions
    cur.execute("SELECT id, description FROM listings WHERE description IS NOT NULL")
    rows = cur.fetchall()

    updated = 0
    for listing_id, description in rows:
        # Process highlights
        result = distill_highlights(description)
        formatted_highlights = [format_highlight(h) for h in result.highlights]
        highlights_json = json.dumps(formatted_highlights)

        # Update the highlights column
        cur.execute(
            "UPDATE listings SET highlights = %s WHERE id = %s",
            (highlights_json, listing_id),
        )
        updated += 1
        print(f"Updated listing {listing_id}: {formatted_highlights}")

    conn.commit()
    print(f"Updated highlights for {updated} listings")

conn.close()

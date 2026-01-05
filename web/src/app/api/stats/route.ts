import { NextResponse } from 'next/server';
import { sql, type Stats } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    // Get counts
    const [counts] = await sql<{ 
      active_listings: string;
      rejected_listings: string;
    }[]>`
      SELECT 
        COUNT(*) FILTER (WHERE is_rejected = false) as active_listings,
        COUNT(*) FILTER (WHERE is_rejected = true) as rejected_listings
      FROM listings
    `;

    const [priceHistoryCount] = await sql<{ count: string }[]>`
      SELECT COUNT(*) as count FROM price_history
    `;

    const [travelTimeCount] = await sql<{ count: string }[]>`
      SELECT COUNT(*) as count FROM travel_times
    `;

    const [destinationCount] = await sql<{ count: string }[]>`
      SELECT COUNT(DISTINCT destination_name) as count FROM travel_times
    `;

    const [priceDropCount] = await sql<{ count: string }[]>`
      SELECT COUNT(*) as count FROM listings l
      JOIN LATERAL (
        SELECT price FROM price_history 
        WHERE listing_id = l.id 
        ORDER BY observed_at ASC LIMIT 1
      ) ph ON true
      WHERE l.is_rejected = false AND l.price < ph.price
    `;

    const [priceStats] = await sql<{
      avg_price: string | null;
      min_price: string | null;
      max_price: string | null;
    }[]>`
      SELECT 
        AVG(price)::int as avg_price,
        MIN(price) as min_price,
        MAX(price) as max_price
      FROM listings
      WHERE is_rejected = false
    `;

    const stats: Stats = {
      active_listings: parseInt(counts?.active_listings || '0'),
      rejected_listings: parseInt(counts?.rejected_listings || '0'),
      price_history_records: parseInt(priceHistoryCount?.count || '0'),
      travel_time_records: parseInt(travelTimeCount?.count || '0'),
      unique_destinations: parseInt(destinationCount?.count || '0'),
      listings_with_price_drops: parseInt(priceDropCount?.count || '0'),
      avg_price: parseInt(priceStats?.avg_price || '0'),
      min_price: parseInt(priceStats?.min_price || '0'),
      max_price: parseInt(priceStats?.max_price || '0'),
    };

    return NextResponse.json(stats);
  } catch (error) {
    console.error('Error fetching stats:', error);
    return NextResponse.json(
      { error: 'Failed to fetch stats' },
      { status: 500 }
    );
  }
}

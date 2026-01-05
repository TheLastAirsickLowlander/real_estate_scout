import { NextResponse } from 'next/server';
import { sql, type PriceHistory } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const history = await sql<(PriceHistory & { address: string; listing_url: string })[]>`
      SELECT 
        ph.id,
        ph.listing_id,
        l.address,
        l.listing_url,
        ph.price,
        ph.zestimate,
        ph.observed_at::text
      FROM price_history ph
      JOIN listings l ON l.id = ph.listing_id
      WHERE l.is_rejected = false
      ORDER BY ph.listing_id, ph.observed_at
    `;

    return NextResponse.json(history);
  } catch (error) {
    console.error('Error fetching price history:', error);
    return NextResponse.json(
      { error: 'Failed to fetch price history' },
      { status: 500 }
    );
  }
}

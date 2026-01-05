import { NextResponse } from 'next/server';
import { sql, type ListingWithTravel, type TravelTime } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const baseFields = sql`
      id, address, price, bedrooms, bathrooms, sqft,
      zestimate, listing_url, zillow_url,
      lat, lng, description,
      features, first_seen::text, last_updated::text, is_rejected
    `;

    // Get all active listings
    let listings: ListingWithTravel[];
    try {
      listings = await sql<ListingWithTravel[]>`
        SELECT 
          ${baseFields},
          status,
          mls_status,
          is_starred,
          viewed_at::text as viewed_at
        FROM listings
        WHERE is_rejected = false
        ORDER BY price ASC
      `;
    } catch {
      listings = await sql<ListingWithTravel[]>`
        SELECT 
          ${baseFields},
          NULL::text as status,
          NULL::text as mls_status,
          false as is_starred,
          NULL::text as viewed_at
        FROM listings
        WHERE is_rejected = false
        ORDER BY price ASC
      `;
    }

    // Get all travel times for non-rejected listings
    const travelTimes = await sql<(TravelTime & { listing_id: number })[]>`
      SELECT 
        tt.id, tt.listing_id, tt.destination_name, tt.destination_address,
        tt.duration_minutes, tt.distance_miles::float, tt.traffic_aware,
        tt.calculated_at::text
      FROM travel_times tt
      JOIN listings l ON l.id = tt.listing_id
      WHERE l.is_rejected = false
    `;

    // Group travel times by listing_id
    const travelByListing = new Map<number, TravelTime[]>();
    for (const tt of travelTimes) {
      if (!travelByListing.has(tt.listing_id)) {
        travelByListing.set(tt.listing_id, []);
      }
      travelByListing.get(tt.listing_id)!.push(tt);
    }

    // Attach travel times to listings
    const listingsWithTravel = listings.map((listing) => ({
      ...listing,
      travel_times: travelByListing.get(listing.id) || [],
    }));

    return NextResponse.json(listingsWithTravel);
  } catch (error) {
    console.error('Error fetching listings:', error);
    return NextResponse.json(
      { error: 'Failed to fetch listings' },
      { status: 500 }
    );
  }
}

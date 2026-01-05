import Link from 'next/link';
import { sql, type ListingWithTravel, type TravelTime } from '@/lib/db';
import { ListingsTable } from '@/components/ListingsTable';

export const dynamic = 'force-dynamic';

async function getRejectedListingsWithTravel(): Promise<ListingWithTravel[]> {
  const baseFields = sql`
    id, address, price, bedrooms, bathrooms, sqft,
    zestimate, listing_url, zillow_url,
    lat, lng, description,
    highlights, features, first_seen::text, last_updated::text, is_rejected
  `;

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
      WHERE is_rejected = true
      ORDER BY last_updated DESC
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
      WHERE is_rejected = true
      ORDER BY last_updated DESC
    `;
  }

  const travelTimes = await sql<(TravelTime & { listing_id: number })[]>`
    SELECT 
      tt.id, tt.listing_id, tt.destination_name, tt.destination_address,
      tt.duration_minutes, tt.distance_miles::float as distance_miles, tt.traffic_aware,
      tt.calculated_at::text
    FROM travel_times tt
    JOIN listings l ON l.id = tt.listing_id
    WHERE l.is_rejected = true
  `;

  const travelByListing = new Map<number, TravelTime[]>();
  for (const tt of travelTimes) {
    if (!travelByListing.has(tt.listing_id)) {
      travelByListing.set(tt.listing_id, []);
    }
    travelByListing.get(tt.listing_id)!.push(tt);
  }

  return listings.map((listing) => ({
    ...listing,
    travel_times: travelByListing.get(listing.id) || [],
  }));
}

async function getDestinationNames(): Promise<string[]> {
  const destinations = await sql<{ destination_name: string }[]>`
    SELECT DISTINCT destination_name
    FROM travel_times
    ORDER BY destination_name
  `;
  return destinations.map((d) => d.destination_name);
}

export default async function RejectedPage() {
  const [listings, destinationNames] = await Promise.all([
    getRejectedListingsWithTravel(),
    getDestinationNames(),
  ]);

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <div className="flex items-baseline justify-between gap-6">
          <div>
            <h1 className="font-[var(--font-serif)] text-4xl italic text-[var(--text-primary)]">
              Rejected Homes
            </h1>
            <p className="mt-2 text-[var(--text-secondary)]">
              Hidden listings - click restore to bring back
            </p>
          </div>
          <Link
            href="/listings"
            className="text-sm text-[var(--accent-cool)] hover:underline"
          >
            Back to listings
          </Link>
        </div>
      </div>

      <div
        className="animate-fade-in"
        style={{ opacity: 0, animationDelay: '0.2s' }}
      >
        <ListingsTable
          listings={listings}
          destinationNames={destinationNames}
          mode="rejected"
        />
      </div>
    </div>
  );
}

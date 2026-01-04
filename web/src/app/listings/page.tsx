import { sql, type ListingWithTravel, type TravelTime } from '@/lib/db';
import { ListingsTable } from '@/components/ListingsTable';

async function getListingsWithTravel(): Promise<ListingWithTravel[]> {
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

  const travelTimes = await sql<(TravelTime & { listing_id: number })[]>`
    SELECT 
      tt.id, tt.listing_id, tt.destination_name, tt.destination_address,
      tt.duration_minutes, tt.distance_miles::float as distance_miles, tt.traffic_aware,
      tt.calculated_at::text
    FROM travel_times tt
    JOIN listings l ON l.id = tt.listing_id
    WHERE l.is_rejected = false
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

function isPendingStatus(listing: ListingWithTravel): boolean {
  const status = (listing.mls_status || listing.status || '').toLowerCase();
  return status.includes('pending') || status.includes('contingent');
}

export default async function ListingsPage() {
  const [listings, destinationNames] = await Promise.all([
    getListingsWithTravel(),
    getDestinationNames(),
  ]);

  const pendingListings = listings.filter(isPendingStatus);
  const starredListings = listings.filter((l) => l.is_starred && !isPendingStatus(l));
  const activeListings = listings.filter((l) => !isPendingStatus(l) && !l.is_starred);

  return (
    <div className="space-y-10">
      <div className="animate-fade-in">
        <h1 className="font-[var(--font-serif)] text-4xl italic text-[var(--text-primary)]">
          Listings
        </h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Browse and filter all active listings
        </p>
      </div>

      {starredListings.length > 0 ? (
        <div className="space-y-4 animate-fade-in" style={{ opacity: 0, animationDelay: '0.2s' }}>
          <div>
            <h2 className="font-[var(--font-serif)] text-2xl italic text-[var(--text-primary)]">
              Starred
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Your favorite listings
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {starredListings.map((l) => (
              <div
                key={l.id}
                className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-[var(--text-primary)] truncate">{l.address}</p>
                    <p className="mt-1 text-sm text-[var(--text-secondary)] whitespace-nowrap">
                      {(l.mls_status || l.status) ?? 'Active'}
                    </p>
                  </div>
                  <p className="font-semibold text-[var(--text-primary)] whitespace-nowrap">
                    ${l.price.toLocaleString()}
                  </p>
                </div>

                {l.highlights && l.highlights.length > 0 ? (
                  <ul className="mt-2 space-y-0.5 text-xs text-[var(--text-secondary)]">
                    {l.highlights.slice(0, 3).map((h, idx) => (
                      <li key={idx} className="truncate">
                        • {h}
                      </li>
                    ))}
                  </ul>
                ) : null}

                <div className="mt-3 flex items-center justify-between text-sm text-[var(--text-secondary)]">
                  <span>
                    {l.bedrooms} bd • {l.bathrooms} ba • {l.sqft.toLocaleString()} sqft
                  </span>
                  <div className="flex items-center gap-3">
                    <a
                      href={l.listing_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--accent-cool)] hover:underline"
                    >
                      Realtor
                    </a>
                    {l.zillow_url ? (
                      <a
                        href={l.zillow_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--accent-cool)] hover:underline"
                      >
                        Zillow
                      </a>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="animate-fade-in" style={{ opacity: 0, animationDelay: '0.3s' }}>
        <ListingsTable listings={activeListings} destinationNames={destinationNames} />
      </div>

      {pendingListings.length > 0 ? (
        <div className="space-y-3 animate-fade-in" style={{ opacity: 0, animationDelay: '0.4s' }}>
          <div>
            <h2 className="font-[var(--font-serif)] text-2xl italic text-[var(--text-primary)]">
              Pending
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Informational only — minimal emphasis
            </p>
          </div>

          <ul className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)]">
            {pendingListings.map((l) => (
              <li
                key={l.id}
                className="px-4 py-3 flex items-center justify-between gap-3 text-sm text-[var(--text-secondary)]"
              >
                <div className="min-w-0">
                  <p className="font-medium text-[var(--text-primary)] truncate">{l.address}</p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {(l.mls_status || l.status) ?? 'Pending'}
                  </p>
                </div>
                <div className="text-right min-w-[160px] space-y-1">
                  <p className="font-semibold text-[var(--text-primary)] whitespace-nowrap">
                    ${l.price.toLocaleString()}
                  </p>
                  <p className="text-xs text-[var(--text-muted)] whitespace-nowrap">
                    {l.bedrooms} bd • {l.bathrooms} ba • {l.sqft.toLocaleString()} sqft
                  </p>
                  <div className="flex items-center justify-end gap-3 text-xs">
                    <a
                      href={l.listing_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--accent-cool)] hover:underline"
                    >
                      Realtor
                    </a>
                    {l.zillow_url ? (
                      <a
                        href={l.zillow_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--accent-cool)] hover:underline"
                      >
                        Zillow
                      </a>
                    ) : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}


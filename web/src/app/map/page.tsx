import { sql, type ListingWithTravel, type TravelTime, type Destination } from '@/lib/db';
import { ListingsMap } from '@/components/ListingsMap';

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

async function getDestinations(): Promise<{ name: string; lat: number; lng: number }[]> {
  // First check if destinations table exists and try to get stored destinations
  try {
    const storedDestinations = await sql<Destination[]>`
      SELECT id, name, address, lat, lng, geocoded_at::text
      FROM destinations
      WHERE lat IS NOT NULL AND lng IS NOT NULL
      ORDER BY name
    `;

    if (storedDestinations.length > 0) {
      return storedDestinations.map((d) => ({
        name: d.name,
        lat: d.lat!,
        lng: d.lng!,
      }));
    }
  } catch {
    // Table doesn't exist yet, fall through to geocoding
  }

  // Fallback: Get unique destinations from travel_times and try to geocode them
  const travelDestinations = await sql<{ destination_name: string; destination_address: string }[]>`
    SELECT DISTINCT destination_name, destination_address
    FROM travel_times
    ORDER BY destination_name
  `;

  // Geocode each destination using Nominatim (with rate limiting)
  const geocodedDestinations: { name: string; lat: number; lng: number }[] = [];
  
  for (const dest of travelDestinations) {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(dest.destination_address)}`,
        {
          headers: {
            'User-Agent': 'RealEstateScout/1.0',
          },
          next: { revalidate: 86400 }, // Cache for 24 hours
        }
      );
      
      if (response.ok) {
        const results = await response.json();
        if (results.length > 0) {
          const { lat, lon } = results[0];
          geocodedDestinations.push({
            name: dest.destination_name,
            lat: parseFloat(lat),
            lng: parseFloat(lon),
          });
          
          // Try to store in database for future use (fire and forget)
          try {
            await sql`
              INSERT INTO destinations (name, address, lat, lng, geocoded_at)
              VALUES (${dest.destination_name}, ${dest.destination_address}, ${parseFloat(lat)}, ${parseFloat(lon)}, NOW())
              ON CONFLICT (name) DO UPDATE SET
                lat = EXCLUDED.lat,
                lng = EXCLUDED.lng,
                geocoded_at = NOW()
            `;
          } catch {
            // Table doesn't exist, ignore
          }
        }
      }
      
      // Rate limit: wait 1 second between requests
      await new Promise((resolve) => setTimeout(resolve, 1000));
    } catch {
      // Geocoding failed, skip this destination
      console.error(`Failed to geocode destination: ${dest.destination_name}`);
    }
  }

  return geocodedDestinations;
}

export default async function MapPage() {
  const [listings, destinations] = await Promise.all([
    getListingsWithTravel(),
    getDestinations(),
  ]);

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <h1 className="font-[var(--font-serif)] text-4xl italic text-[var(--text-primary)]">
          Map View
        </h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Explore listings and travel times on the map
        </p>
      </div>

      <div className="animate-fade-in" style={{ opacity: 0, animationDelay: '0.2s' }}>
        <ListingsMap listings={listings} destinations={destinations} />
      </div>

      {/* Quick stats below map */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in" style={{ opacity: 0, animationDelay: '0.4s' }}>
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-4">
          <p className="text-sm text-[var(--text-secondary)]">Total Listings</p>
          <p className="text-2xl font-semibold text-[var(--text-primary)]">{listings.length}</p>
        </div>
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-4">
          <p className="text-sm text-[var(--text-secondary)]">With Travel Data</p>
          <p className="text-2xl font-semibold text-[var(--text-primary)]">
            {listings.filter(l => l.travel_times.length > 0).length}
          </p>
        </div>
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-4">
          <p className="text-sm text-[var(--text-secondary)]">Avg Bedrooms</p>
          <p className="text-2xl font-semibold text-[var(--text-primary)]">
            {listings.length > 0 
              ? (listings.reduce((sum, l) => sum + l.bedrooms, 0) / listings.length).toFixed(1)
              : 0}
          </p>
        </div>
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-4">
          <p className="text-sm text-[var(--text-secondary)]">Avg Sqft</p>
          <p className="text-2xl font-semibold text-[var(--text-primary)]">
            {listings.length > 0 
              ? Math.round(listings.reduce((sum, l) => sum + l.sqft, 0) / listings.length).toLocaleString()
              : 0}
          </p>
        </div>
      </div>
    </div>
  );
}

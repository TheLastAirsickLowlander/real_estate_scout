import postgres from 'postgres';

const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  throw new Error('DATABASE_URL environment variable is not set');
}

// Create a single shared connection for the application
export const sql = postgres(connectionString, {
  max: 10,
  idle_timeout: 20,
  connect_timeout: 10,
});

// Type definitions matching the PostgreSQL schema
export interface Listing {
  id: number;
  address: string;
  price: number;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  zestimate: number | null;
  listing_url: string;
  zillow_url: string | null;
  status: string | null;
  mls_status: string | null;
  lat: number;
  lng: number;
  description: string;
  highlights: string[];
  features: string[];
  first_seen: string;
  last_updated: string;
  is_rejected: boolean;
  is_starred: boolean;
  viewed_at: string | null;
}

export interface TravelTime {
  id: number;
  listing_id: number;
  destination_name: string;
  destination_address: string;
  duration_minutes: number;
  distance_miles: number;
  traffic_aware: boolean;
  calculated_at: string;
}

export interface PriceHistory {
  id: number;
  listing_id: number;
  price: number;
  zestimate: number | null;
  observed_at: string;
}

export interface ListingWithTravel extends Listing {
  travel_times: TravelTime[];
}

export interface Stats {
  active_listings: number;
  rejected_listings: number;
  price_history_records: number;
  travel_time_records: number;
  unique_destinations: number;
  listings_with_price_drops: number;
  avg_price: number;
  min_price: number;
  max_price: number;
}

export interface Destination {
  id: number;
  name: string;
  address: string;
  lat: number | null;
  lng: number | null;
  geocoded_at: string | null;
}

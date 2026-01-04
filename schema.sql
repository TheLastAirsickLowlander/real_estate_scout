-- Real Estate Scout Database Schema
-- PostgreSQL

-- Main listings table
CREATE TABLE IF NOT EXISTS listings (
    id SERIAL PRIMARY KEY,
    address TEXT NOT NULL,
    price INTEGER NOT NULL,
    bedrooms INTEGER NOT NULL,
    bathrooms NUMERIC(3,1) NOT NULL,
    sqft INTEGER NOT NULL,
    zestimate INTEGER,
    listing_url TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    description TEXT,
    features JSONB DEFAULT '[]'::jsonb,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Use listing_url as unique identifier (contains MLS ID)
    CONSTRAINT unique_listing_url UNIQUE (listing_url)
);

-- Price history for tracking changes
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    price INTEGER NOT NULL,
    zestimate INTEGER,
    observed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Travel times cache
CREATE TABLE IF NOT EXISTS travel_times (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    destination_name TEXT NOT NULL,
    destination_address TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    distance_miles NUMERIC(6,2) NOT NULL,
    traffic_aware BOOLEAN DEFAULT FALSE,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- One travel time per listing-destination pair
    CONSTRAINT unique_listing_destination UNIQUE (listing_id, destination_name)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_listings_address ON listings(address);
CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(price);
CREATE INDEX IF NOT EXISTS idx_listings_last_updated ON listings(last_updated);
CREATE INDEX IF NOT EXISTS idx_listings_is_active ON listings(is_active);
CREATE INDEX IF NOT EXISTS idx_listings_location ON listings(lat, lng);

CREATE INDEX IF NOT EXISTS idx_price_history_listing ON price_history(listing_id);
CREATE INDEX IF NOT EXISTS idx_price_history_observed ON price_history(observed_at);

CREATE INDEX IF NOT EXISTS idx_travel_times_listing ON travel_times(listing_id);
CREATE INDEX IF NOT EXISTS idx_travel_times_destination ON travel_times(destination_name);

-- Destinations table for storing geocoded destination coordinates
CREATE TABLE IF NOT EXISTS destinations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    geocoded_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_destination_name UNIQUE (name)
);

CREATE INDEX IF NOT EXISTS idx_destinations_name ON destinations(name);

-- View for listings with price drops
CREATE OR REPLACE VIEW listings_with_price_changes AS
SELECT 
    l.id,
    l.address,
    l.price AS current_price,
    ph_first.price AS first_price,
    ph_lowest.min_price AS lowest_price,
    l.price - ph_first.price AS price_change,
    ROUND(((l.price - ph_first.price)::numeric / ph_first.price) * 100, 1) AS price_change_pct,
    l.first_seen,
    l.last_updated
FROM listings l
LEFT JOIN LATERAL (
    SELECT price 
    FROM price_history 
    WHERE listing_id = l.id 
    ORDER BY observed_at ASC 
    LIMIT 1
) ph_first ON true
LEFT JOIN LATERAL (
    SELECT MIN(price) as min_price
    FROM price_history 
    WHERE listing_id = l.id
) ph_lowest ON true
WHERE l.is_active = TRUE;

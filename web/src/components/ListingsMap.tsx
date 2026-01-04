'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import type { ListingWithTravel, TravelTime } from '@/lib/db';
import { formatPrice } from '@/lib/utils';

// Dynamically import map components to avoid SSR issues
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
);
const Marker = dynamic(
  () => import('react-leaflet').then((mod) => mod.Marker),
  { ssr: false }
);
const Popup = dynamic(
  () => import('react-leaflet').then((mod) => mod.Popup),
  { ssr: false }
);
const Circle = dynamic(
  () => import('react-leaflet').then((mod) => mod.Circle),
  { ssr: false }
);

interface ListingsMapProps {
  listings: ListingWithTravel[];
  destinations: { name: string; lat: number; lng: number }[];
}

export function ListingsMap({ listings, destinations }: ListingsMapProps) {
  const [mounted, setMounted] = useState(false);
  const [selectedListing, setSelectedListing] = useState<ListingWithTravel | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="h-[600px] bg-[var(--bg-accent)] rounded-xl flex items-center justify-center">
        <p className="text-[var(--text-muted)]">Loading map...</p>
      </div>
    );
  }

  // Calculate map center from listings or default to Orlando
  const center: [number, number] = listings.length > 0
    ? [
        listings.reduce((sum, l) => sum + l.lat, 0) / listings.length,
        listings.reduce((sum, l) => sum + l.lng, 0) / listings.length,
      ]
    : [28.5383, -81.3792]; // Orlando

  // Price-based coloring
  const getMarkerColor = (price: number): string => {
    const prices = listings.map(l => l.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const ratio = (price - min) / (max - min || 1);
    
    if (ratio < 0.33) return '#16a34a'; // Green - lower price
    if (ratio < 0.66) return '#d97706'; // Amber - mid price
    return '#dc2626'; // Red - higher price
  };

  // Get travel time circle radius (convert minutes to meters, rough approximation)
  const getTravelRadius = (minutes: number): number => {
    // Assume ~40 km/h average speed, so minutes * 667 meters
    return minutes * 667;
  };

  return (
    <div className="relative">
      {/* Import Leaflet CSS */}
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
        crossOrigin=""
      />
      
      <MapContainer
        center={center}
        zoom={11}
        className="h-[600px] rounded-xl z-0"
        style={{ background: 'var(--bg-accent)' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Destination markers and labels */}
        {destinations.map((dest, index) => (
          <Marker
            key={`dest-marker-${index}`}
            position={[dest.lat, dest.lng]}
          >
            <Popup>
              <div className="min-w-[120px]">
                <p className="font-semibold text-[var(--text-primary)]">
                  {dest.name}
                </p>
                <p className="text-xs text-[var(--text-muted)]">Destination</p>
              </div>
            </Popup>
          </Marker>
        ))}
        
        {/* Destination circles (visual indicator) */}
        {destinations.map((dest, index) => (
          <Circle
            key={`dest-circle-${index}`}
            center={[dest.lat, dest.lng]}
            radius={500}
            pathOptions={{
              color: '#0284c7',
              fillColor: '#0284c7',
              fillOpacity: 0.3,
              weight: 2,
            }}
          />
        ))}

        {/* Listing markers */}
        {listings.map((listing) => (
          <Marker
            key={listing.id}
            position={[listing.lat, listing.lng]}
            eventHandlers={{
              click: () => setSelectedListing(listing),
            }}
          >
            <Popup>
              <div className="min-w-[200px]">
                <p className="font-semibold text-[var(--text-primary)] mb-1">
                  {formatPrice(listing.price)}
                </p>
                <p className="text-sm text-[var(--text-secondary)] mb-2">
                  {listing.address}
                </p>
                <p className="text-xs text-[var(--text-muted)]">
                  {listing.bedrooms} bed &middot; {listing.bathrooms} bath &middot; {listing.sqft.toLocaleString()} sqft
                </p>
                {listing.travel_times.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-[var(--border)]">
                    <p className="text-xs font-medium text-[var(--text-secondary)] mb-1">Travel Times:</p>
                    {listing.travel_times.map((tt: TravelTime) => (
                      <p key={tt.destination_name} className="text-xs text-[var(--text-muted)]">
                        {tt.destination_name}: {tt.duration_minutes} min
                      </p>
                    ))}
                  </div>
                )}
                <div className="mt-2 flex items-center gap-3">
                  <a
                    href={listing.listing_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block text-xs text-[var(--accent-cool)] hover:underline"
                  >
                    Realtor &rarr;
                  </a>
                  {listing.zillow_url && (
                    <a
                      href={listing.zillow_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block text-xs text-[var(--accent-cool)] hover:underline"
                    >
                      Zillow &rarr;
                    </a>
                  )}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Travel time circles for selected listing */}
        {selectedListing && selectedListing.travel_times.map((tt: TravelTime, index: number) => (
          <Circle
            key={`travel-${index}`}
            center={[selectedListing.lat, selectedListing.lng]}
            radius={getTravelRadius(tt.duration_minutes)}
            pathOptions={{
              color: '#d97706',
              fillColor: '#d97706',
              fillOpacity: 0.1,
              weight: 1,
              dashArray: '5, 5',
            }}
          />
        ))}
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-3 z-[1000]">
        <p className="text-xs font-medium text-[var(--text-primary)] mb-2">Price Range</p>
        <div className="flex items-center gap-2 text-xs">
          <span className="w-3 h-3 rounded-full bg-[#16a34a]"></span>
          <span className="text-[var(--text-secondary)]">Lower</span>
          <span className="w-3 h-3 rounded-full bg-[#d97706] ml-2"></span>
          <span className="text-[var(--text-secondary)]">Mid</span>
          <span className="w-3 h-3 rounded-full bg-[#dc2626] ml-2"></span>
          <span className="text-[var(--text-secondary)]">Higher</span>
        </div>
      </div>

      {/* Stats overlay */}
      <div className="absolute top-4 right-4 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-3 z-[1000]">
        <p className="text-sm font-medium text-[var(--text-primary)]">
          {listings.length} listings
        </p>
        <p className="text-xs text-[var(--text-muted)]">
          {destinations.length} destinations
        </p>
      </div>
    </div>
  );
}

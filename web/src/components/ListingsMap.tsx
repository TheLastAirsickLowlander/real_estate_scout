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

// Component to handle map events and selection - needs access to useMap
const MapController = dynamic(
  () => import('react-leaflet').then((mod) => {
    const { useMap } = mod;
    return function MapControllerInner({ 
      selectedId, 
      listings,
    }: { 
      selectedId: number | null; 
      listings: ListingWithTravel[];
    }) {
      const map = useMap();
      
      useEffect(() => {
        if (selectedId !== null) {
          const listing = listings.find(l => l.id === selectedId);
          if (listing) {
            map.flyTo([listing.lat, listing.lng], 14, { duration: 0.5 });
          }
        }
      }, [selectedId, listings, map]);
      
      return null;
    };
  }),
  { ssr: false }
);

// Individual marker component that handles its own popup state
const ListingMarker = dynamic(
  () => import('react-leaflet').then((mod) => {
    const { Marker: RLMarker, Popup: RLPopup, useMap } = mod;
    const L = require('leaflet');
    
    return function ListingMarkerInner({
      listing,
      icon,
      isSelected,
      onSelect,
    }: {
      listing: ListingWithTravel;
      icon: L.DivIcon;
      isSelected: boolean;
      onSelect?: (id: number) => void;
    }) {
      const map = useMap();
      const [markerRef, setMarkerRef] = useState<L.Marker | null>(null);
      
      useEffect(() => {
        if (isSelected && markerRef) {
          // Small delay to let flyTo complete
          const timer = setTimeout(() => {
            markerRef.openPopup();
          }, 600);
          return () => clearTimeout(timer);
        }
      }, [isSelected, markerRef]);
      
      return (
        <RLMarker
          position={[listing.lat, listing.lng]}
          icon={icon}
          ref={setMarkerRef}
          eventHandlers={{
            click: () => onSelect?.(listing.id),
          }}
        >
          <RLPopup>
            <div className="min-w-[200px]">
              <div className="flex items-center gap-2 mb-1">
                {listing.is_starred && (
                  <span className="text-amber-500">★</span>
                )}
                <p className="font-semibold text-[var(--text-primary)]">
                  {formatPrice(listing.price)}
                </p>
              </div>
              <p className="text-sm text-[var(--text-secondary)] mb-2">
                {listing.address}
              </p>
              <p className="text-xs text-[var(--text-muted)]">
                {listing.bedrooms} bed &middot; {listing.bathrooms} bath &middot; {listing.sqft.toLocaleString()} sqft
              </p>
              {listing.highlights && listing.highlights.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {listing.highlights.map((highlight: string, idx: number) => (
                    <span
                      key={idx}
                      className="inline-block px-1.5 py-0.5 text-[10px] bg-[var(--bg-accent)] text-[var(--text-secondary)] rounded"
                    >
                      {highlight}
                    </span>
                  ))}
                </div>
              )}
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
          </RLPopup>
        </RLMarker>
      );
    };
  }),
  { ssr: false }
);

interface ListingsMapProps {
  listings: ListingWithTravel[];
  destinations: { name: string; lat: number; lng: number }[];
  selectedId?: number | null;
  onSelect?: (id: number) => void;
}

// SVG icons as data URIs
const createStarIcon = (L: typeof import('leaflet')) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32">
    <filter id="shadow-star" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="1" flood-opacity="0.3"/>
    </filter>
    <path filter="url(#shadow-star)" fill="#F59E0B" stroke="#B45309" stroke-width="1" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
  </svg>`;
  return L.divIcon({
    html: svg,
    className: 'custom-star-icon',
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

const createDestinationIcon = (L: typeof import('leaflet')) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="40">
    <filter id="shadow-dest" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="1" flood-opacity="0.3"/>
    </filter>
    <path filter="url(#shadow-dest)" fill="#DC2626" stroke="#991B1B" stroke-width="1" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
  </svg>`;
  return L.divIcon({
    html: svg,
    className: 'custom-destination-icon',
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -40],
  });
};

const createDefaultIcon = (L: typeof import('leaflet')) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="36">
    <filter id="shadow-default" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="1" flood-opacity="0.3"/>
    </filter>
    <path filter="url(#shadow-default)" fill="#3B82F6" stroke="#1D4ED8" stroke-width="1" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
  </svg>`;
  return L.divIcon({
    html: svg,
    className: 'custom-default-icon',
    iconSize: [28, 36],
    iconAnchor: [14, 36],
    popupAnchor: [0, -36],
  });
};

export function ListingsMap({ 
  listings, 
  destinations, 
  selectedId = null,
  onSelect 
}: ListingsMapProps) {
  const [mounted, setMounted] = useState(false);
  const [icons, setIcons] = useState<{
    star: L.DivIcon | null;
    destination: L.DivIcon | null;
    default: L.DivIcon | null;
  }>({ star: null, destination: null, default: null });

  useEffect(() => {
    setMounted(true);
    // Create icons after mount (client-side only)
    const L = require('leaflet');
    setIcons({
      star: createStarIcon(L),
      destination: createDestinationIcon(L),
      default: createDefaultIcon(L),
    });
  }, []);

  if (!mounted || !icons.default) {
    return (
      <div className="h-full bg-[var(--bg-accent)] rounded-xl flex items-center justify-center">
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

  return (
    <div className="relative h-full">
      {/* Import Leaflet CSS */}
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
        crossOrigin=""
      />
      
      {/* Custom icon styles */}
      <style>{`
        .custom-star-icon,
        .custom-destination-icon,
        .custom-default-icon {
          background: transparent;
          border: none;
        }
      `}</style>
      
      <MapContainer
        center={center}
        zoom={11}
        className="h-full rounded-xl z-0"
        style={{ background: 'var(--bg-accent)' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Map controller for selection handling */}
        <MapController 
          selectedId={selectedId} 
          listings={listings}
        />

        {/* Destination markers with red pin icons */}
        {destinations.map((dest, index) => (
          <Marker
            key={`dest-marker-${index}`}
            position={[dest.lat, dest.lng]}
            icon={icons.destination!}
          >
            <Popup>
              <div className="min-w-[120px]">
                <p className="font-semibold text-[var(--text-primary)]">
                  {dest.name}
                </p>
                <p className="text-xs text-[var(--text-muted)]">Travel Destination</p>
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
              color: '#DC2626',
              fillColor: '#DC2626',
              fillOpacity: 0.15,
              weight: 2,
            }}
          />
        ))}

        {/* Listing markers */}
        {listings.map((listing) => (
          <ListingMarker
            key={listing.id}
            listing={listing}
            icon={listing.is_starred ? icons.star! : icons.default!}
            isSelected={selectedId === listing.id}
            onSelect={onSelect}
          />
        ))}
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg p-3 z-[1000]">
        <p className="text-xs font-medium text-[var(--text-primary)] mb-2">Legend</p>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-amber-500 text-base">★</span>
            <span className="text-[var(--text-secondary)]">Starred</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-blue-500 text-base">●</span>
            <span className="text-[var(--text-secondary)]">Listing</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-red-500 text-base">●</span>
            <span className="text-[var(--text-secondary)]">Destination</span>
          </div>
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

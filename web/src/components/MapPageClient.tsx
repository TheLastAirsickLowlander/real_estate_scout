'use client';

import { useState, useMemo, useCallback } from 'react';
import { ListingsMap } from './ListingsMap';
import { MapListPanel, type SortOrder } from './MapListPanel';
import type { ListingWithTravel } from '@/lib/db';

interface MapPageClientProps {
  listings: ListingWithTravel[];
  destinations: { name: string; lat: number; lng: number }[];
  mode?: 'active' | 'rejected';
}

export function MapPageClient({ listings: initialListings, destinations, mode = 'active' }: MapPageClientProps) {
  const [listings, setListings] = useState<ListingWithTravel[]>(initialListings);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('starred');

  const handleToggleStar = useCallback(async (id: number, starred: boolean) => {
    // Optimistically update UI
    setListings(prev => prev.map(listing => 
      listing.id === id ? { ...listing, is_starred: starred } : listing
    ));

    try {
      const response = await fetch(`/api/listings/${id}/star`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ starred }),
      });

      if (!response.ok) {
        // Revert on error
        setListings(prev => prev.map(listing => 
          listing.id === id ? { ...listing, is_starred: !starred } : listing
        ));
        console.error('Failed to update star status');
      }
    } catch (error) {
      // Revert on error
      setListings(prev => prev.map(listing => 
        listing.id === id ? { ...listing, is_starred: !starred } : listing
      ));
      console.error('Failed to update star status:', error);
    }
  }, []);

  const handleToggleRejected = useCallback(async (id: number, rejected: boolean) => {
    // For rejected mode, we remove the listing from the list when unrejected
    const originalListings = listings;
    
    // Optimistically remove from list
    setListings(prev => prev.filter(listing => listing.id !== id));
    
    // Clear selection if this was the selected listing
    if (selectedId === id) {
      setSelectedId(null);
    }

    try {
      const response = await fetch(`/api/listings/${id}/rejected`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejected }),
      });

      if (!response.ok) {
        // Revert on error
        setListings(originalListings);
        console.error('Failed to update rejected status');
      }
    } catch (error) {
      // Revert on error
      setListings(originalListings);
      console.error('Failed to update rejected status:', error);
    }
  }, [listings, selectedId]);

  const sortedListings = useMemo(() => {
    const sorted = [...listings];
    
    switch (sortOrder) {
      case 'starred':
        // Starred first, then by price ascending
        sorted.sort((a, b) => {
          if (a.is_starred && !b.is_starred) return -1;
          if (!a.is_starred && b.is_starred) return 1;
          return a.price - b.price;
        });
        break;
      case 'price-asc':
        sorted.sort((a, b) => a.price - b.price);
        break;
      case 'price-desc':
        sorted.sort((a, b) => b.price - a.price);
        break;
    }
    
    return sorted;
  }, [listings, sortOrder]);

  return (
    <div className="flex h-[calc(100vh-160px)] gap-4">
      <div className="flex-1 min-w-0">
        <ListingsMap
          listings={listings}
          destinations={destinations}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onReject={mode === 'active' ? (id) => handleToggleRejected(id, true) : undefined}
          onToggleStar={handleToggleStar}
        />
      </div>
      <MapListPanel
        listings={sortedListings}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onToggleStar={handleToggleStar}
        onToggleRejected={mode === 'rejected' ? handleToggleRejected : undefined}
        sortOrder={sortOrder}
        onSortChange={setSortOrder}
        mode={mode}
      />
    </div>
  );
}

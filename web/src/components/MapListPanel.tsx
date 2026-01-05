'use client';

import { Star, RotateCcw } from 'lucide-react';
import type { ListingWithTravel } from '@/lib/db';
import { formatPrice } from '@/lib/utils';

export type SortOrder = 'starred' | 'price-asc' | 'price-desc';

interface MapListPanelProps {
  listings: ListingWithTravel[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onToggleStar: (id: number, starred: boolean) => void;
  onToggleRejected?: (id: number, rejected: boolean) => void;
  sortOrder: SortOrder;
  onSortChange: (order: SortOrder) => void;
  mode?: 'active' | 'rejected';
}

export function MapListPanel({
  listings,
  selectedId,
  onSelect,
  onToggleStar,
  onToggleRejected,
  sortOrder,
  onSortChange,
  mode = 'active',
}: MapListPanelProps) {
  const handleStarClick = (e: React.MouseEvent, listing: ListingWithTravel) => {
    e.stopPropagation();
    onToggleStar(listing.id, !listing.is_starred);
  };

  const handleUnrejectClick = (e: React.MouseEvent, listing: ListingWithTravel) => {
    e.stopPropagation();
    onToggleRejected?.(listing.id, false);
  };

  return (
    <div className="w-80 flex flex-col bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
      {/* Header with sort controls */}
      <div className="p-3 border-b border-[var(--border)]">
        <p className="text-sm font-medium text-[var(--text-primary)] mb-2">
          {listings.length} {mode === 'rejected' ? 'Rejected' : 'Listings'}
        </p>
        
        {/* Segmented sort buttons */}
        <div className="flex rounded-lg bg-[var(--bg-accent)] p-0.5">
          <button
            onClick={() => onSortChange('starred')}
            className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${
              sortOrder === 'starred'
                ? 'bg-[var(--bg-secondary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
          >
            <Star size={12} fill={sortOrder === 'starred' ? '#F59E0B' : 'none'} stroke={sortOrder === 'starred' ? '#F59E0B' : 'currentColor'} />
            First
          </button>
          <button
            onClick={() => onSortChange('price-asc')}
            className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${
              sortOrder === 'price-asc'
                ? 'bg-[var(--bg-secondary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
          >
            Price &uarr;
          </button>
          <button
            onClick={() => onSortChange('price-desc')}
            className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${
              sortOrder === 'price-desc'
                ? 'bg-[var(--bg-secondary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
          >
            Price &darr;
          </button>
        </div>
      </div>

      {/* Scrollable listings */}
      <div className="flex-1 overflow-y-auto">
        {listings.map((listing) => (
          <div
            key={listing.id}
            onClick={() => onSelect(listing.id)}
            className={`w-full text-left p-3 border-b border-[var(--border)] transition-colors hover:bg-[var(--bg-accent)] cursor-pointer ${
              selectedId === listing.id
                ? 'bg-[var(--bg-accent)] border-l-2 border-l-[var(--accent-cool)]'
                : ''
            }`}
          >
            <div className="flex items-start gap-2">
              <div className="flex flex-col gap-1 flex-shrink-0 mt-0.5">
                <button
                  onClick={(e) => handleStarClick(e, listing)}
                  className="p-0.5 rounded hover:bg-[var(--bg-accent)] transition-colors"
                  title={listing.is_starred ? 'Remove star' : 'Add star'}
                >
                  <Star
                    size={14}
                    fill={listing.is_starred ? '#F59E0B' : 'none'}
                    stroke={listing.is_starred ? '#F59E0B' : 'var(--text-muted)'}
                    className={listing.is_starred ? '' : 'hover:stroke-amber-500'}
                  />
                </button>
                {mode === 'rejected' && onToggleRejected && (
                  <button
                    onClick={(e) => handleUnrejectClick(e, listing)}
                    className="p-0.5 rounded hover:bg-[var(--bg-accent)] transition-colors"
                    title="Restore listing"
                  >
                    <RotateCcw
                      size={14}
                      stroke="var(--text-muted)"
                      className="hover:stroke-green-500"
                    />
                  </button>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {listing.address}
                </p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-sm font-semibold text-[var(--accent-cool)]">
                    {formatPrice(listing.price)}
                  </span>
                  <span className="text-xs text-[var(--text-muted)]">
                    {listing.bedrooms}bd {listing.bathrooms}ba
                  </span>
                </div>
                {listing.highlights && listing.highlights.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {listing.highlights.slice(0, 3).map((highlight, idx) => (
                      <span
                        key={idx}
                        className="inline-block px-1.5 py-0.5 text-[10px] bg-[var(--bg-accent)] text-[var(--text-secondary)] rounded"
                      >
                        {highlight}
                      </span>
                    ))}
                    {listing.highlights.length > 3 && (
                      <span className="text-[10px] text-[var(--text-muted)]">
                        +{listing.highlights.length - 3}
                      </span>
                    )}
                  </div>
                )}
                {listing.travel_times.length > 0 && (
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    {listing.travel_times.map(t => `${t.duration_minutes}m`).join(' / ')}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}

        {listings.length === 0 && (
          <div className="p-4 text-center text-[var(--text-muted)] text-sm">
            No listings found
          </div>
        )}
      </div>
    </div>
  );
}

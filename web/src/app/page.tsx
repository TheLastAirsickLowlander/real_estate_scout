import { sql, type Stats, type ListingWithTravel } from '@/lib/db';
import { formatPrice, formatNumber } from '@/lib/utils';
import { 
  Home, 
  TrendingDown, 
  Clock, 
  MapPin,
  DollarSign,
  ArrowDown,
  ArrowUp
} from 'lucide-react';
import Link from 'next/link';

async function getStats(): Promise<Stats> {
  const [counts] = await sql<{ 
    active_listings: string;
    rejected_listings: string;
  }[]>`
    SELECT 
      COUNT(*) FILTER (WHERE is_rejected = false) as active_listings,
      COUNT(*) FILTER (WHERE is_rejected = true) as rejected_listings
    FROM listings
  `;

  const [priceHistoryCount] = await sql<{ count: string }[]>`
    SELECT COUNT(*) as count FROM price_history
  `;

  const [travelTimeCount] = await sql<{ count: string }[]>`
    SELECT COUNT(*) as count FROM travel_times
  `;

  const [destinationCount] = await sql<{ count: string }[]>`
    SELECT COUNT(DISTINCT destination_name) as count FROM travel_times
  `;

  const [priceDropCount] = await sql<{ count: string }[]>`
    SELECT COUNT(*) as count FROM listings l
    JOIN LATERAL (
      SELECT price FROM price_history 
      WHERE listing_id = l.id 
      ORDER BY observed_at ASC LIMIT 1
    ) ph ON true
    WHERE l.is_rejected = false AND l.price < ph.price
  `;

  const [priceStats] = await sql<{
    avg_price: string | null;
    min_price: string | null;
    max_price: string | null;
  }[]>`
    SELECT 
      AVG(price)::int as avg_price,
      MIN(price) as min_price,
      MAX(price) as max_price
    FROM listings
    WHERE is_rejected = false
  `;

  return {
    active_listings: parseInt(counts?.active_listings || '0'),
    rejected_listings: parseInt(counts?.rejected_listings || '0'),
    price_history_records: parseInt(priceHistoryCount?.count || '0'),
    travel_time_records: parseInt(travelTimeCount?.count || '0'),
    unique_destinations: parseInt(destinationCount?.count || '0'),
    listings_with_price_drops: parseInt(priceDropCount?.count || '0'),
    avg_price: parseInt(priceStats?.avg_price || '0'),
    min_price: parseInt(priceStats?.min_price || '0'),
    max_price: parseInt(priceStats?.max_price || '0'),
  };
}

async function getRecentListings(): Promise<ListingWithTravel[]> {
  const listings = await sql<ListingWithTravel[]>`
    SELECT 
      id, address, price, bedrooms, bathrooms, sqft,
      listing_url, lat, lng, first_seen::text, last_updated::text,
      NULL::text as status, NULL::text as mls_status,
      NULL::int as zestimate, NULL::text as zillow_url, ''::text as description,
      '[]'::jsonb as features, false as is_rejected
    FROM listings
    WHERE is_rejected = false
    ORDER BY first_seen DESC
    LIMIT 5
  `;
  return listings.map(l => ({ ...l, travel_times: [] }));
}

async function getPriceDrops(): Promise<{ address: string; price: number; original_price: number; listing_url: string }[]> {
  return sql`
    SELECT 
      l.address,
      l.price,
      l.listing_url,
      ph_first.price AS original_price
    FROM listings l
    JOIN LATERAL (
      SELECT price 
      FROM price_history 
      WHERE listing_id = l.id 
      ORDER BY observed_at ASC 
      LIMIT 1
    ) ph_first ON true
    WHERE l.is_rejected = false
      AND l.price < ph_first.price
    ORDER BY (l.price - ph_first.price) ASC
    LIMIT 5
  `;
}

export default async function Dashboard() {
  const [stats, recentListings, priceDrops] = await Promise.all([
    getStats(),
    getRecentListings(),
    getPriceDrops(),
  ]);

  const statCards = [
    {
      label: 'Listings',
      value: formatNumber(stats.active_listings),
      icon: Home,
      color: 'var(--accent-cool)',
    },
    {
      label: 'Rejected',
      value: formatNumber(stats.rejected_listings),
      icon: Home,
      color: 'var(--text-muted)',
    },
    {
      label: 'Price Drops',
      value: formatNumber(stats.listings_with_price_drops),
      icon: TrendingDown,
      color: 'var(--accent-success)',
    },
    {
      label: 'Avg Price',
      value: formatPrice(stats.avg_price),
      icon: DollarSign,
      color: 'var(--accent-warm)',
    },
    {
      label: 'Destinations Tracked',
      value: formatNumber(stats.unique_destinations),
      icon: MapPin,
      color: 'var(--accent-cool)',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="animate-fade-in">
        <h1 className="font-[var(--font-serif)] text-4xl italic text-[var(--text-primary)]">
          Dashboard
        </h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Overview of your real estate search
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className={`stat-card bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5 animate-fade-in animate-delay-${index + 1}`}
              style={{ opacity: 0 }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-[var(--text-secondary)] font-medium">
                    {stat.label}
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">
                    {stat.value}
                  </p>
                </div>
                <div 
                  className="p-2 rounded-lg"
                  style={{ backgroundColor: `${stat.color}15` }}
                >
                  <Icon size={20} style={{ color: stat.color }} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Listings */}
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6 animate-fade-in" style={{ opacity: 0, animationDelay: '0.5s' }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-lg text-[var(--text-primary)]">
              Recent Listings
            </h2>
            <Link 
              href="/listings" 
              className="text-sm text-[var(--accent-cool)] hover:underline"
            >
              View all
            </Link>
          </div>
          
          <div className="space-y-3">
            {recentListings.length === 0 ? (
              <p className="text-[var(--text-muted)] text-sm py-4">
                No listings found. Run the ETL pipeline to fetch data.
              </p>
            ) : (
              recentListings.map((listing) => (
                <a
                  key={listing.id}
                  href={listing.listing_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 rounded-lg border border-[var(--border)] hover:border-[var(--border-strong)] transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-[var(--text-primary)] truncate">
                        {listing.address}
                      </p>
                      <p className="text-sm text-[var(--text-secondary)] mt-1">
                        {listing.bedrooms} bed &middot; {listing.bathrooms} bath &middot; {formatNumber(listing.sqft)} sqft
                      </p>
                    </div>
                    <p className="font-semibold text-[var(--text-primary)] ml-4">
                      {formatPrice(listing.price)}
                    </p>
                  </div>
                </a>
              ))
            )}
          </div>
        </div>

        {/* Price Drops */}
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6 animate-fade-in" style={{ opacity: 0, animationDelay: '0.6s' }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-lg text-[var(--text-primary)]">
              Price Drops
            </h2>
            <Link 
              href="/prices" 
              className="text-sm text-[var(--accent-cool)] hover:underline"
            >
              View history
            </Link>
          </div>
          
          <div className="space-y-3">
            {priceDrops.length === 0 ? (
              <p className="text-[var(--text-muted)] text-sm py-4">
                No price drops detected yet.
              </p>
            ) : (
              priceDrops.map((drop, index) => {
                const savings = drop.original_price - drop.price;
                const pct = ((savings / drop.original_price) * 100).toFixed(1);
                
                return (
                  <a
                    key={index}
                    href={drop.listing_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 rounded-lg border border-[var(--border)] hover:border-[var(--border-strong)] transition-colors"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-[var(--text-primary)] truncate">
                          {drop.address}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm text-[var(--text-muted)] line-through">
                            {formatPrice(drop.original_price)}
                          </span>
                          <ArrowDown size={14} className="text-[var(--accent-success)]" />
                          <span className="text-sm font-medium text-[var(--accent-success)]">
                            {formatPrice(drop.price)}
                          </span>
                        </div>
                      </div>
                      <div className="text-right ml-4">
                        <span className="inline-block px-2 py-1 bg-[var(--accent-success)] bg-opacity-10 text-[var(--accent-success)] text-xs font-semibold rounded">
                          -{pct}%
                        </span>
                      </div>
                    </div>
                  </a>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Price Range */}
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6 animate-fade-in" style={{ opacity: 0, animationDelay: '0.7s' }}>
        <h2 className="font-semibold text-lg text-[var(--text-primary)] mb-4">
          Price Range
        </h2>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="h-2 bg-[var(--bg-accent)] rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-[var(--accent-success)] via-[var(--accent-warm)] to-[var(--accent-danger)]"
                style={{ width: '100%' }}
              />
            </div>
            <div className="flex justify-between mt-2 text-sm">
              <span className="text-[var(--text-secondary)]">
                Min: {formatPrice(stats.min_price)}
              </span>
              <span className="font-medium text-[var(--text-primary)]">
                Avg: {formatPrice(stats.avg_price)}
              </span>
              <span className="text-[var(--text-secondary)]">
                Max: {formatPrice(stats.max_price)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

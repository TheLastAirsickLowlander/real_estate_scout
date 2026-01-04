'use client';

import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { formatPrice } from '@/lib/utils';

interface PriceHistoryEntry {
  listing_id: number;
  address: string;
  price: number;
  observed_at: string;
}

interface PriceChartProps {
  history: PriceHistoryEntry[];
}

const COLORS = [
  '#0284c7', // blue
  '#d97706', // amber
  '#16a34a', // green
  '#dc2626', // red
  '#8b5cf6', // purple
  '#06b6d4', // cyan
  '#f43f5e', // rose
  '#84cc16', // lime
];

export function PriceChart({ history }: PriceChartProps) {
  const { chartData, listings } = useMemo(() => {
    // Group by listing_id
    const byListing = new Map<number, { address: string; data: { date: string; price: number }[] }>();
    
    for (const entry of history) {
      if (!byListing.has(entry.listing_id)) {
        byListing.set(entry.listing_id, { address: entry.address, data: [] });
      }
      byListing.get(entry.listing_id)!.data.push({
        date: new Date(entry.observed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        price: entry.price,
      });
    }

    // Create chart data with all dates
    const allDates = new Set<string>();
    byListing.forEach((listing) => {
      listing.data.forEach((d) => allDates.add(d.date));
    });

    const sortedDates = Array.from(allDates).sort((a, b) => 
      new Date(a).getTime() - new Date(b).getTime()
    );

    const listings = Array.from(byListing.entries()).map(([id, data]) => ({
      id,
      address: data.address,
      shortAddress: data.address.split(',')[0], // First part of address
    }));

    const chartData = sortedDates.map((date) => {
      const point: Record<string, number | string> = { date };
      byListing.forEach((listing, id) => {
        const entry = listing.data.find((d) => d.date === date);
        if (entry) {
          point[`listing_${id}`] = entry.price;
        }
      });
      return point;
    });

    return { chartData, listings };
  }, [history]);

  if (history.length === 0) {
    return (
      <div className="h-[400px] bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl flex items-center justify-center">
        <p className="text-[var(--text-muted)]">No price history data available</p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6">
      <h3 className="font-semibold text-lg text-[var(--text-primary)] mb-4">
        Price History Over Time
      </h3>
      
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis 
            dataKey="date" 
            stroke="var(--text-muted)"
            fontSize={12}
          />
          <YAxis 
            stroke="var(--text-muted)"
            fontSize={12}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value) => [formatPrice(value as number), 'Price']}
          />
          <Legend 
            wrapperStyle={{ fontSize: '12px' }}
            formatter={(value) => {
              const listing = listings.find((l) => `listing_${l.id}` === value);
              return listing?.shortAddress || value;
            }}
          />
          {listings.map((listing, index) => (
            <Line
              key={listing.id}
              type="monotone"
              dataKey={`listing_${listing.id}`}
              name={`listing_${listing.id}`}
              stroke={COLORS[index % COLORS.length]}
              strokeWidth={2}
              dot={{ fill: COLORS[index % COLORS.length], strokeWidth: 0, r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Legend with full addresses */}
      <div className="mt-4 pt-4 border-t border-[var(--border)]">
        <p className="text-xs text-[var(--text-muted)] mb-2">Listings:</p>
        <div className="flex flex-wrap gap-3">
          {listings.map((listing, index) => (
            <div key={listing.id} className="flex items-center gap-2">
              <span 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
              <span className="text-xs text-[var(--text-secondary)] truncate max-w-[200px]">
                {listing.shortAddress}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

import { sql } from '@/lib/db';
import { PriceChart } from '@/components/PriceChart';
import { formatPrice, formatNumber } from '@/lib/utils';
import { ArrowDown, TrendingDown } from 'lucide-react';

export const dynamic = 'force-dynamic';

interface PriceHistoryEntry {
  id: number;
  listing_id: number;
  address: string;
  listing_url: string;
  price: number;
  zestimate: number | null;
  observed_at: string;
}

interface PriceDrop {
  address: string;
  listing_url: string;
  current_price: number;
  original_price: number;
  drop_amount: number;
  drop_percent: number;
}

async function getPriceHistory(): Promise<PriceHistoryEntry[]> {
  return sql`
    SELECT 
      ph.id,
      ph.listing_id,
      l.address,
      l.listing_url,
      ph.price,
      ph.zestimate,
      ph.observed_at::text
    FROM price_history ph
    JOIN listings l ON l.id = ph.listing_id
    WHERE l.is_rejected = false
    ORDER BY ph.listing_id, ph.observed_at
  `;
}

async function getPriceDrops(): Promise<PriceDrop[]> {
  return sql`
    SELECT 
      l.address,
      l.listing_url,
      l.price AS current_price,
      ph_first.price AS original_price,
      (ph_first.price - l.price) AS drop_amount,
      ROUND(((ph_first.price - l.price)::numeric / ph_first.price * 100), 1) AS drop_percent
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
    ORDER BY drop_amount DESC
  `;
}

export default async function PricesPage() {
  const [history, priceDrops] = await Promise.all([
    getPriceHistory(),
    getPriceDrops(),
  ]);

  const totalSavings = priceDrops.reduce((sum, d) => sum + d.drop_amount, 0);

  return (
    <div className="space-y-8">
      <div className="animate-fade-in">
        <h1 className="font-[var(--font-serif)] text-4xl italic text-[var(--text-primary)]">
          Price History
        </h1>
        <p className="mt-2 text-[var(--text-secondary)]">
          Track price changes and find deals
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-fade-in" style={{ opacity: 0, animationDelay: '0.1s' }}>
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--accent-success)] bg-opacity-10">
              <TrendingDown size={20} className="text-[var(--accent-success)]" />
            </div>
            <div>
              <p className="text-sm text-[var(--text-secondary)]">Price Drops</p>
              <p className="text-2xl font-semibold text-[var(--text-primary)]">
                {priceDrops.length}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--accent-success)] bg-opacity-10">
              <ArrowDown size={20} className="text-[var(--accent-success)]" />
            </div>
            <div>
              <p className="text-sm text-[var(--text-secondary)]">Total Savings Available</p>
              <p className="text-2xl font-semibold text-[var(--accent-success)]">
                {formatPrice(totalSavings)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--accent-cool)] bg-opacity-10">
              <TrendingDown size={20} className="text-[var(--accent-cool)]" />
            </div>
            <div>
              <p className="text-sm text-[var(--text-secondary)]">Price Records</p>
              <p className="text-2xl font-semibold text-[var(--text-primary)]">
                {formatNumber(history.length)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="animate-fade-in" style={{ opacity: 0, animationDelay: '0.2s' }}>
        <PriceChart history={history} />
      </div>

      {/* Price Drops Table */}
      <div className="animate-fade-in" style={{ opacity: 0, animationDelay: '0.3s' }}>
        <h2 className="font-semibold text-xl text-[var(--text-primary)] mb-4">
          All Price Drops
        </h2>
        
        {priceDrops.length === 0 ? (
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-8 text-center">
            <p className="text-[var(--text-muted)]">No price drops detected yet.</p>
          </div>
        ) : (
          <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border)]">
                    <th className="px-4 py-3 text-left text-sm font-medium text-[var(--text-secondary)]">
                      Address
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-[var(--text-secondary)]">
                      Original
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-[var(--text-secondary)]">
                      Current
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-[var(--text-secondary)]">
                      Savings
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-[var(--text-secondary)]">
                      Drop
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {priceDrops.map((drop, index) => (
                    <tr 
                      key={index}
                      className="table-row-hover border-b border-[var(--border)] last:border-0"
                    >
                      <td className="px-4 py-3">
                        <a
                          href={drop.listing_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-[var(--text-primary)] hover:text-[var(--accent-cool)] truncate block max-w-[300px]"
                        >
                          {drop.address}
                        </a>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-sm text-[var(--text-muted)] line-through">
                          {formatPrice(drop.original_price)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-semibold text-[var(--text-primary)]">
                          {formatPrice(drop.current_price)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-medium text-[var(--accent-success)]">
                          {formatPrice(drop.drop_amount)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="inline-block px-2 py-1 bg-[var(--accent-success)] bg-opacity-10 text-[var(--accent-success)] text-xs font-semibold rounded">
                          -{drop.drop_percent}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

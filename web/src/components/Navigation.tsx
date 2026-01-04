'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Map, Table, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Dashboard', icon: Home },
  { href: '/map', label: 'Map', icon: Map },
  { href: '/listings', label: 'Listings', icon: Table },
  { href: '/prices', label: 'Price History', icon: TrendingDown },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <header className="border-b border-[var(--border)] bg-[var(--bg-secondary)]">
      <div className="w-full px-6">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent-warm)] flex items-center justify-center">
              <span className="text-white font-bold text-sm">RS</span>
            </div>
            <span className="font-[var(--font-serif)] text-xl italic text-[var(--text-primary)]">
              Real Estate Scout
            </span>
          </Link>

          <nav className="flex items-center gap-8">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'nav-link flex items-center gap-2 text-sm font-medium py-1',
                    isActive 
                      ? 'text-[var(--text-primary)]' 
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
                    isActive && 'active'
                  )}
                >
                  <Icon size={16} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}

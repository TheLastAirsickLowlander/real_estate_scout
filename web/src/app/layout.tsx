import type { Metadata } from 'next';
import './globals.css';
import { Navigation } from '@/components/Navigation';

export const metadata: Metadata = {
  title: 'Real Estate Scout',
  description: 'Real estate listings dashboard with travel analysis',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <Navigation />
          <main className="w-full px-6 py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}

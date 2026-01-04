'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type ColumnFiltersState,
  type ColumnDef,
} from '@tanstack/react-table';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ExternalLink,
  Search,
  Star,
  StarOff,
  Eye,
  EyeOff,
} from 'lucide-react';
import type { ListingWithTravel, TravelTime } from '@/lib/db';
import { formatPrice, formatNumber, cn } from '@/lib/utils';

interface ListingsTableProps {
  listings: ListingWithTravel[];
  destinationNames: string[];
  mode?: 'active' | 'rejected';
}

const columnHelper = createColumnHelper<ListingWithTravel>();

export function ListingsTable({
  listings,
  destinationNames,
  mode = 'active',
}: ListingsTableProps) {
  const router = useRouter();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);

  const columns = useMemo(() => {
    const setRejected = async (listingId: number, rejected: boolean) => {
      const resp = await fetch(`/api/listings/${listingId}/rejected`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejected }),
      });

      if (!resp.ok) {
        throw new Error('Failed to update rejected status');
      }

      router.refresh();
    };

    const baseColumns: ColumnDef<ListingWithTravel, any>[] = [
      columnHelper.accessor('address', {
        header: 'Address',
        cell: (info) => {
          const listing = info.row.original;
          const highlights = listing.highlights || [];

          return (
            <div className="max-w-[420px]">
              <p className="font-medium text-[var(--text-primary)] truncate">
                {info.getValue()}
              </p>

              {highlights.length > 0 ? (
                <ul className="mt-1 space-y-0.5 text-xs text-[var(--text-secondary)]">
                  {highlights.slice(0, 3).map((h, idx) => (
                    <li key={idx} className="truncate">
                      • {h}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          );
        },
      }),
      columnHelper.accessor((row) => row.mls_status || row.status || null, {
        id: 'status',
        header: 'Status',
        cell: (info) => {
          const value = info.getValue() as string | null;
          if (!value) {
            return <span className="text-[var(--text-muted)]">-</span>;
          }
          return <span className="whitespace-nowrap">{value}</span>;
        },
      }),
      columnHelper.accessor('is_starred', {
        header: '',
        cell: ({ row }) => {
          const listingId = row.original.id;
          const isStarred = row.original.is_starred;

          return (
            <button
              type="button"
              className={cn(
                'inline-flex items-center justify-center h-8 w-8 rounded-md',
isStarred
                  ? 'text-[#d4af37] hover:bg-[var(--bg-secondary)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
              )}
              title={isStarred ? 'Unstar' : 'Star'}
               onClick={async () => {
                 try {
                   setActionError(null);
                   const resp = await fetch(`/api/listings/${listingId}/star`, {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({ starred: !isStarred }),
                   });

                   if (!resp.ok) {
                     const text = await resp.text().catch(() => '');
                     setActionError(text || 'Failed to update starred status');
                     return;
                   }

                   router.refresh();
                 } catch (err) {
                   setActionError(err instanceof Error ? err.message : 'Failed to update starred status');
                 }
               }}
            >
              {isStarred ? <Star size={16} /> : <StarOff size={16} />}
            </button>
          );
        },
        enableSorting: true,
        sortingFn: (rowA, rowB, columnId) => {
          const a = rowA.getValue(columnId) as boolean;
          const b = rowB.getValue(columnId) as boolean;
          if (a === b) return 0;
          return a ? -1 : 1;
        },
      }),
      columnHelper.accessor('viewed_at', {
        header: '',
        cell: ({ row }) => {
          const listingId = row.original.id;
          const isViewed = Boolean(row.original.viewed_at);

          return (
            <button
              type="button"
              className={cn(
                'inline-flex items-center justify-center h-8 w-8 rounded-md',
                isViewed
                  ? 'text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
              )}
              title={isViewed ? 'Mark unviewed' : 'Mark viewed'}
               onClick={async () => {
                 try {
                   setActionError(null);
                   const resp = await fetch(`/api/listings/${listingId}/viewed`, {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({ viewed: !isViewed }),
                   });

                   if (!resp.ok) {
                     const text = await resp.text().catch(() => '');
                     setActionError(text || 'Failed to update viewed status');
                     return;
                   }

                   router.refresh();
                 } catch (err) {
                   setActionError(err instanceof Error ? err.message : 'Failed to update viewed status');
                 }
               }}
            >
              {isViewed ? <Eye size={16} /> : <EyeOff size={16} />}
            </button>
          );
        },
        enableSorting: true,
        sortingFn: (rowA, rowB, columnId) => {
          const a = rowA.getValue(columnId) as string | null;
          const b = rowB.getValue(columnId) as string | null;
          // Put unviewed (null) before viewed
          if (a === null && b === null) return 0;
          if (a === null) return -1;
          if (b === null) return 1;
          return a.localeCompare(b);
        },
      }),
      columnHelper.accessor('price', {
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-[var(--text-primary)]"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Price
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp size={14} />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown size={14} />
            ) : (
              <ArrowUpDown size={14} className="opacity-50" />
            )}
          </button>
        ),
        cell: (info) => (
          <span className="font-semibold text-[var(--text-primary)]">
            {formatPrice(info.getValue())}
          </span>
        ),
      }),
      columnHelper.accessor('bedrooms', {
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-[var(--text-primary)]"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Beds
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp size={14} />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown size={14} />
            ) : (
              <ArrowUpDown size={14} className="opacity-50" />
            )}
          </button>
        ),
        cell: (info) => info.getValue(),
      }),
      columnHelper.accessor('bathrooms', {
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-[var(--text-primary)]"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Baths
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp size={14} />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown size={14} />
            ) : (
              <ArrowUpDown size={14} className="opacity-50" />
            )}
          </button>
        ),
        cell: (info) => info.getValue(),
      }),
      columnHelper.accessor('sqft', {
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 hover:text-[var(--text-primary)]"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Sqft
            {column.getIsSorted() === 'asc' ? (
              <ArrowUp size={14} />
            ) : column.getIsSorted() === 'desc' ? (
              <ArrowDown size={14} />
            ) : (
              <ArrowUpDown size={14} className="opacity-50" />
            )}
          </button>
        ),
        cell: (info) => formatNumber(info.getValue()),
      }),
    ];

    // Add a column for each destination
    const commuteColumns: ColumnDef<ListingWithTravel, any>[] = destinationNames.map((destName) =>
      columnHelper.accessor(
        (row) => {
          const travel = row.travel_times.find((t) => t.destination_name === destName);
          return travel?.duration_minutes ?? null;
        },
        {
          id: `commute_${destName}`,
          header: ({ column }) => (
            <button
              className="flex items-center gap-1 hover:text-[var(--text-primary)] whitespace-nowrap"
              onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            >
              {destName}
              {column.getIsSorted() === 'asc' ? (
                <ArrowUp size={14} />
              ) : column.getIsSorted() === 'desc' ? (
                <ArrowDown size={14} />
              ) : (
                <ArrowUpDown size={14} className="opacity-50" />
              )}
            </button>
          ),
          cell: (info) => {
            const minutes = info.getValue() as number | null;
            if (minutes === null) {
              return <span className="text-[var(--text-muted)]">-</span>;
            }
            return (
              <span
                className={cn(
                  'font-medium',
                  minutes <= 20
                    ? 'text-[var(--accent-success)]'
                    : minutes <= 35
                    ? 'text-[var(--accent-warm)]'
                    : 'text-[var(--accent-danger)]'
                )}
              >
                {minutes} min
              </span>
            );
          },
          sortingFn: (rowA, rowB, columnId) => {
            const a = rowA.getValue(columnId) as number | null;
            const b = rowB.getValue(columnId) as number | null;
            // Put nulls at the end
            if (a === null && b === null) return 0;
            if (a === null) return 1;
            if (b === null) return -1;
            return a - b;
          },
        }
      )
    );

    const linksColumn: ColumnDef<ListingWithTravel, any> = columnHelper.display({
      id: 'links',
      header: 'Links',
      cell: ({ row }) => {
        const listingId = row.original.id;
        const listingUrl = row.original.listing_url;
        const zillowUrl = row.original.zillow_url;

        return (
          <div className="flex items-center gap-4 whitespace-nowrap">
            <div className="flex items-center gap-3">
              <a
                href={listingUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-[var(--accent-cool)] hover:underline"
              >
                Realtor <ExternalLink size={12} />
              </a>
              {zillowUrl ? (
                <a
                  href={zillowUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-[var(--accent-cool)] hover:underline"
                >
                  Zillow <ExternalLink size={12} />
                </a>
              ) : (
                <span className="text-sm text-[var(--text-muted)]">Zillow -</span>
              )}
            </div>

            <button
              type="button"
              className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              onClick={() =>
                setRejected(listingId, mode === 'active')
              }
            >
              {mode === 'active' ? 'Reject' : 'Undo'}
            </button>
          </div>
        );
      },
      enableSorting: false,
    });

    return [...baseColumns, ...commuteColumns, linksColumn];
  }, [destinationNames, mode, router]);

  const table = useReactTable({
    data: listings,
    columns,
    state: {
      sorting,
      globalFilter,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="flex flex-col gap-4 h-[calc(100vh-220px)]">
      {/* Search */}
      <div className="relative">
        <Search 
          size={16} 
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" 
        />
        <input
          type="text"
          placeholder="Search listings..."
          value={globalFilter ?? ''}
          onChange={(e) => setGlobalFilter(e.target.value)}
          className="w-full max-w-sm pl-10 pr-4 py-2 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-cool)]"
        />
      </div>

      {actionError ? (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] px-4 py-2 text-sm text-[var(--accent-danger)]">
          {actionError}
        </div>
      ) : null}

      {/* Table */}
      <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl overflow-hidden flex-1 min-h-0">
        <div className="overflow-x-auto h-full">
          <table className="w-full min-w-full">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id} className="border-b border-[var(--border)]">
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-3 text-left text-sm font-medium text-[var(--text-secondary)]"
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td 
                    colSpan={columns.length} 
                    className="px-4 py-12 text-center text-[var(--text-muted)]"
                  >
                    No listings found
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <tr 
                    key={row.id} 
                    className={cn(
                      'table-row-hover border-b border-[var(--border)] last:border-0',
                      row.original.is_starred ? 'bg-[var(--bg-primary)]' : null,
                      row.original.viewed_at ? 'opacity-80' : null
                    )}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3 text-sm">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Results count */}
      <p className="text-sm text-[var(--text-muted)]">
        Showing {table.getFilteredRowModel().rows.length} of {listings.length} listings
      </p>
    </div>
  );
}

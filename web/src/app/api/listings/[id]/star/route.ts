import { NextResponse } from 'next/server';
import { sql } from '@/lib/db';

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const listingId = Number(params.id);
    if (!Number.isFinite(listingId)) {
      return NextResponse.json({ error: 'Invalid listing id' }, { status: 400 });
    }

    const body = (await request.json().catch(() => null)) as
      | { starred?: boolean }
      | null;
    const starred = !!body?.starred;

    let updated:
      | { id: number; is_starred: boolean }
      | undefined;

    try {
      [updated] = await sql<{ id: number; is_starred: boolean }[]>`
        UPDATE listings
        SET is_starred = ${starred}
        WHERE id = ${listingId}
        RETURNING id, is_starred
      `;
    } catch {
      // Backward compatible with DBs that haven't had migrations applied yet.
      return NextResponse.json(
        { error: 'is_starred column missing (run ETL --init-db)' },
        { status: 400 }
      );
    }

    if (!updated) {
      return NextResponse.json({ error: 'Listing not found' }, { status: 404 });
    }

    return NextResponse.json(updated);
  } catch (error) {
    console.error('Error updating listing starred status:', error);
    return NextResponse.json(
      { error: 'Failed to update starred status' },
      { status: 500 }
    );
  }
}

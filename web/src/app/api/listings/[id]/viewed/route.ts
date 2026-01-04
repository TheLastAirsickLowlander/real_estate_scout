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
      | { viewed?: boolean }
      | null;
    const viewed = !!body?.viewed;

    let updated:
      | { id: number; viewed_at: string | null }
      | undefined;

    try {
      [updated] = await sql<{ id: number; viewed_at: string | null }[]>`
        UPDATE listings
        SET viewed_at = CASE WHEN ${viewed} THEN NOW() ELSE NULL END
        WHERE id = ${listingId}
        RETURNING id, viewed_at::text
      `;
    } catch {
      // Backward compatible with DBs that haven't had migrations applied yet.
      return NextResponse.json(
        { error: 'viewed_at column missing (run ETL --init-db)' },
        { status: 400 }
      );
    }

    if (!updated) {
      return NextResponse.json({ error: 'Listing not found' }, { status: 404 });
    }

    return NextResponse.json(updated);
  } catch (error) {
    console.error('Error updating listing viewed status:', error);
    return NextResponse.json(
      { error: 'Failed to update viewed status' },
      { status: 500 }
    );
  }
}

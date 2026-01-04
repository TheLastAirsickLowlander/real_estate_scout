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
      | { rejected?: boolean }
      | null;
    const rejected = !!body?.rejected;

    const [updated] = await sql<{ id: number; is_rejected: boolean }[]>`
      UPDATE listings
      SET is_rejected = ${rejected}
      WHERE id = ${listingId}
      RETURNING id, is_rejected
    `;

    if (!updated) {
      return NextResponse.json({ error: 'Listing not found' }, { status: 404 });
    }

    return NextResponse.json(updated);
  } catch (error) {
    console.error('Error updating listing rejected status:', error);
    return NextResponse.json(
      { error: 'Failed to update rejected status' },
      { status: 500 }
    );
  }
}

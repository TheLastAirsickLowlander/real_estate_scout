# AGENTS.md - Real Estate Scout

Real Estate Scout = Python ETL + Postgres + Next.js dashboard.

## Layout

- `etl/`: HomeHarvest ingest, scoring, travel-time (OSRM/Nominatim), DB writes
- `web/`: Next.js app (Bun), maps/charts/tables on same Postgres DB
- `exports/`: generated reports

## Quick Commands

```bash
# ETL
pip install -r requirements.txt
python -m etl.main
python -m etl.main --no-travel
python -m etl.main --export all
python -m etl.main --stats

# Web
cd web
bun install
bun run dev
bun run build
bun start
```

## Database / psql

Prefer verifying schema/data with `psql` (faster than writing migrations by hand).
Connection string lives in `web/.env.local`.

```bash
psql "$(rg -N "^DATABASE_URL=" web/.env.local | cut -d= -f2-)"
psql "$(rg -N "^DATABASE_URL=" web/.env.local | cut -d= -f2-)" -c "SELECT COUNT(*) FROM listings;"
```

## Python (ETL) Standards

- Python 3.10+, full type hints, dataclasses, `pathlib.Path`
- Use `logging` (not `print`), context managers for resources
- External APIs: OSRM + Nominatim are ~1 req/sec; always rate-limit (e.g. `time.sleep(1.1)`)

(Optional tooling)
```bash
pip install ruff black mypy
black etl/
ruff check etl/
mypy etl/
```

## TypeScript / Web Standards

- Strict TypeScript, avoid `any`
- Prefer Server Components for data fetching
- DB access uses direct SQL via `sql` in `web/src/lib/db.ts` (no heavy ORM)

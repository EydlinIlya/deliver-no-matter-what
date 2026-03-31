# CLAUDE.md

## Project overview

"Deliver No Matter What" generates GitHub profile badges showing time spent in bomb shelters (from Israeli Home Front Command alerts) alongside GitHub contribution counts.

## Architecture

```
GitHub README → Supabase Edge Function (serve-badge) → SVG
Vercel (static site) → Supabase Auth + JS SDK → badges table
GitHub Actions (cron ~hourly) → Python → Supabase PostgreSQL
```

- **Supabase Edge Functions** (Deno/TypeScript): `serve-badge`, `init-badge`, `serve-areas`
- **Supabase PostgreSQL**: 4 tables — `badges`, `badge_data_cache`, `area_times`, `csv_cache`
- **Supabase Auth**: GitHub OAuth (only `read:user` scope, no tokens stored)
- **GitHub Actions**: `update-badges.yml` runs `update_badges.py` every 15 min (throttled to ~hourly)
- **Vercel**: static site (`site/index.html`, `site/dashboard.html`)

## Key files

- `src/am_israel_hai_badge/update_badges.py` — GH Actions entry point
- `src/am_israel_hai_badge/db.py` — Database layer (PostgreSQL + SQLite)
- `src/am_israel_hai_badge/cache.py` — AlertCache (shelter time computation)
- `src/am_israel_hai_badge/shelter.py` — State machine: alerts → shelter sessions
- `src/am_israel_hai_badge/api.py` — Tzevaadom API client, GitHub GraphQL, CSV cache
- `supabase/functions/serve-badge/index.ts` — Badge SVG generation
- `supabase/functions/init-badge/index.ts` — On-create contribution fetch
- `site/index.html` — Landing page with GitHub OAuth login
- `site/dashboard.html` — Badge CRUD dashboard

## Database

All tables use RLS. `badges.token` is the primary key. Foreign keys cascade deletes.

```
badges (token PK, user_id FK→auth.users, github_login, area_name, created_at)
  └─ badge_data_cache (token FK CASCADE, commits, updated_at)
area_times (area_name PK, s_24h, s_7d, s_30d, updated_at)
csv_cache (name PK, content, updated_at)
```

## Secrets

- `DATABASE_URL` — Supabase PostgreSQL connection pooler (port 6543)
- `GH_PAT` — Bot GitHub PAT (zero scopes, used for public contribution queries)
- Both set in GitHub Actions secrets AND Supabase Edge Function secrets

## Common commands

```bash
# Deploy Edge Functions
npx supabase functions deploy serve-badge --project-ref ttnjqiyfixfxuosuocow --no-verify-jwt
npx supabase functions deploy init-badge --project-ref ttnjqiyfixfxuosuocow --no-verify-jwt

# Run SQL on live DB
npx supabase db query --linked "SELECT * FROM badges;"

# Trigger GH Actions manually
gh workflow run update-badges.yml

# Test badge
curl https://ttnjqiyfixfxuosuocow.supabase.co/functions/v1/serve-badge/{token}
```

## Shelter time calculation

State machine in `shelter.py`:
1. Alert (preparatory/active) → enter shelter
2. Safety signal → exit shelter
3. No signal for 45 min → auto-close (exit = last alert + 10 min)
4. Time windows (24h/7d/30d) clip sessions at boundaries

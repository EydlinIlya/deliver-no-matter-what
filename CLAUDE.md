# CLAUDE.md

GitHub badge showing bomb shelter time + contributions. Supabase (Edge Functions + Auth + PostgreSQL), Vercel (static site), GitHub Actions (cron).

## Key files

- `src/am_israel_hai_badge/update_badges.py` — GH Actions entry point
- `src/am_israel_hai_badge/db.py` — DB layer (PG + SQLite)
- `src/am_israel_hai_badge/cache.py` — Shelter time computation
- `src/am_israel_hai_badge/shelter.py` — Alert → session state machine
- `supabase/functions/serve-badge/index.ts` — SVG generation
- `supabase/functions/init-badge/index.ts` — On-create contribution fetch
- `site/index.html` — Landing page
- `site/dashboard.html` — Badge CRUD

## Database

```
badges (token PK, user_id FK→auth.users CASCADE, github_login, area_name, created_at)
  └─ badge_data_cache (token FK CASCADE, commits, updated_at)
area_times (area_name PK, s_24h, s_7d, s_30d, updated_at)
csv_cache (name PK, content, updated_at)
```

## Commands

```bash
npx supabase functions deploy serve-badge --project-ref ttnjqiyfixfxuosuocow --no-verify-jwt
npx supabase db query --linked "SELECT * FROM badges;"
gh workflow run update-badges.yml
```

## Secrets

`DATABASE_URL` (PG pooler, port 6543), `GH_PAT` (bot PAT, zero scopes). Both in GH Actions + Supabase Edge Function secrets.

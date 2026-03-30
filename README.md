# Deliver No Matter What

A badge that tracks how much time you spend in a bomb shelter, based on real-time Home Front Command alerts for your area.

Sign in with GitHub, pick your area, get a badge URL. Embed it in your profile README or anywhere else.

**[Get your badge](https://deliver-no-matter-what.onrender.com)**

---

## How it works

1. Sign in with GitHub
2. Search for your area (any language)
3. Copy the embed code into your README

The badge shows shelter time for the last 24 hours, 7 days, and 30 days, plus your GitHub contribution count.

Alert data from [tzevaadom.co.il](https://tzevaadom.co.il/) API. City translations from [peppermint-ice/how-the-lion-roars](https://github.com/peppermint-ice/how-the-lion-roars).

---

## Self-hosting

```bash
pip install .[web]
uvicorn am_israel_hai_badge.web.app:app --host 0.0.0.0 --port 8000
```

Requires `SUPABASE_URL`, `SUPABASE_KEY`, and `SESSION_SECRET` environment variables for auth. See `src/am_israel_hai_badge/web/auth.py` for details.

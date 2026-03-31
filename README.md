# Deliver No Matter What

A badge that tracks how much time you spend in a bomb shelter along with your GitHub activity, based on real-time Home Front Command alerts for your area.

Sign in with GitHub, pick your area, get a badge URL. Embed it in your profile README or anywhere else.

**[Get your badge](https://deliver-no-matter-what.vercel.app/)**

---

## How it works

1. Sign in with GitHub (used only to identify your username -- we store no tokens or private data)
2. Search for your area (any language)
3. Click Create
4. Copy the embed code into your README

The badge shows shelter time for the last 24 hours, 7 days, and 30 days, plus your GitHub contribution count.

## How shelter time is calculated

Shelter time is computed from Home Front Command alert data using a state machine:

1. An **alert** (preparatory or active) for your area starts a shelter session
2. The session ends when either:
   - A **safety signal** is received, or
   - **45 minutes pass** with no further alerts (auto-close, with the session ending 10 minutes after the last alert)
3. Sessions that span time window boundaries (24h / 7d / 30d) are **clipped**, not dropped -- only the portion within the window counts
4. Ongoing sessions (no exit signal yet) count time up to the current moment
5. Contribution count is your total GitHub contributions in the last 30 days (public data via GitHub GraphQL API)

Alert data from [tzevaadom.co.il](https://tzevaadom.co.il/) API. City translations from [peppermint-ice/how-the-lion-roars](https://github.com/peppermint-ice/how-the-lion-roars).

## After the war

When the war ends, every badge will be transformed into a permanent record showing **total hours spent in shelter** and **total GitHub contributions** from the start of the war to its end. A testament to everyone who kept delivering no matter what.

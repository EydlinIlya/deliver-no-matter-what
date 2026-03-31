# Deliver No Matter What

A badge showing time spent in bomb shelters + GitHub contributions, based on real-time Home Front Command alerts.

**[Get your badge](https://deliver-no-matter-what.vercel.app/)** — sign in with GitHub, pick your area, embed in your README.

Sign in only identifies your GitHub username. No tokens or private data are stored.

---

## How shelter time is calculated

Alerts for your area start a shelter session. It ends on a safety signal, or auto-closes 10 min after the last alert if nothing arrives within 45 min. Sessions crossing window boundaries (24h/7d/30d) are clipped, not dropped. Contributions are public GitHub activity via GraphQL API.

Data from [tzevaadom.co.il](https://tzevaadom.co.il/). City translations from [peppermint-ice/how-the-lion-roars](https://github.com/peppermint-ice/how-the-lion-roars).

## After the war

When the war ends, badges will transform into permanent records: total hours in shelter and total contributions from start to finish.

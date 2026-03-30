const CITIES_URL =
  "https://raw.githubusercontent.com/peppermint-ice/how-the-lion-roars/refs/heads/main/cities.json";

let cachedAreas: Array<Record<string, string>> | null = null;
let cacheTime = 0;
const CACHE_TTL = 3600_000; // 1 hour

async function fetchAreas(): Promise<Array<Record<string, string>>> {
  if (cachedAreas && Date.now() - cacheTime < CACHE_TTL) return cachedAreas;

  const resp = await fetch(CITIES_URL);
  const data = await resp.json();
  const cities = data.cities || data;

  const areas: Array<Record<string, string>> = [];
  for (const [he, info] of Object.entries(cities)) {
    if (typeof info !== "object" || info === null) continue;
    const entry: Record<string, string> = { he };
    const rec = info as Record<string, string>;
    if (rec.en) entry.en = rec.en;
    if (rec.ru) entry.ru = rec.ru;
    if (rec.ar) entry.ar = rec.ar;
    areas.push(entry);
  }
  areas.sort((a, b) => (a.en || a.he).localeCompare(b.en || b.he));

  cachedAreas = areas;
  cacheTime = Date.now();
  return areas;
}

Deno.serve(async () => {
  try {
    const areas = await fetchAreas();
    return new Response(JSON.stringify(areas), {
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "public, max-age=3600, s-maxage=3600",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: "Failed to fetch areas" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
});

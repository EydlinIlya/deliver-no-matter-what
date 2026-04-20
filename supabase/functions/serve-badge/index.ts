import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

function formatDuration(totalSeconds: number): string {
  totalSeconds = Math.max(0, Math.floor(totalSeconds));
  if (totalSeconds === 0) return "0m";
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours && minutes) return `${hours}h ${minutes}m`;
  if (hours) return `${hours}h`;
  return `${minutes}m`;
}

function generateBadge(
  s24h: number,
  s7d: number,
  s30d: number,
  commits: number,
): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="420" height="120" viewBox="0 0 420 120">
  <rect width="420" height="120" fill="#f8f9fa"/>
  <rect width="420" height="120" fill="none" stroke="#e4beba" stroke-width="1" rx="2" opacity="0.3"/>
  <rect x="0" y="0" width="4" height="120" fill="#b10726"/>
  <text font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="16" font-weight="800">
    <tspan x="18" y="28" fill="#191c1d">Deliver </tspan><tspan fill="#b10726">No Matter What</tspan>
  </text>
  <text x="406" y="28" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" font-weight="600" fill="#5b403d" text-anchor="end" letter-spacing="1">${commits} contributions / 30d</text>
  <text x="18" y="46" font-family="'Segoe UI', system-ui, sans-serif" font-size="13" font-weight="500" fill="#5b403d">Time spent in bomb shelter in:</text>
  <rect x="4" y="54" width="416" height="66" fill="#2e3132"/>
  <rect x="144" y="62" width="1" height="50" fill="#e4beba" opacity="0.15"/>
  <rect x="284" y="62" width="1" height="50" fill="#e4beba" opacity="0.15"/>
  <text x="74" y="78" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" font-weight="600" fill="#e4beba" text-anchor="middle" letter-spacing="0.5">Last 24 hours</text>
  <text x="74" y="104" font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="22" font-weight="700" fill="#f0f1f2" text-anchor="middle">${formatDuration(s24h)}</text>
  <text x="214" y="78" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" font-weight="600" fill="#e4beba" text-anchor="middle" letter-spacing="0.5">Last 7 days</text>
  <text x="214" y="104" font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="22" font-weight="700" fill="#f0f1f2" text-anchor="middle">${formatDuration(s7d)}</text>
  <text x="354" y="78" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" font-weight="600" fill="#e4beba" text-anchor="middle" letter-spacing="0.5">Last 30 days</text>
  <text x="354" y="104" font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="22" font-weight="700" fill="#f0f1f2" text-anchor="middle">${formatDuration(s30d)}</text>
</svg>`;
}

function generateWarBadge(
  sWar: number,
  warCommits: number,
): string {
  // Blue accent colour replaces red throughout
  return `<svg xmlns="http://www.w3.org/2000/svg" width="420" height="120" viewBox="0 0 420 120">
  <rect width="420" height="120" fill="#f8f9fa"/>
  <rect width="420" height="120" fill="none" stroke="#bed0e4" stroke-width="1" rx="2" opacity="0.3"/>
  <rect x="0" y="0" width="4" height="120" fill="#1d4ed8"/>
  <text font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="16" font-weight="800">
    <tspan x="18" y="28" fill="#191c1d">Deliver </tspan><tspan fill="#1d4ed8">No Matter What</tspan>
  </text>
  <text x="406" y="28" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" font-weight="600" fill="#3d527a" text-anchor="end" letter-spacing="1">Feb 26 – Apr 16, 2026</text>
  <text x="18" y="46" font-family="'Segoe UI', system-ui, sans-serif" font-size="13" font-weight="500" fill="#3d527a">Delivering during the war:</text>
  <rect x="4" y="54" width="416" height="66" fill="#1e2d4a"/>
  <rect x="213" y="62" width="1" height="50" fill="#bed0e4" opacity="0.15"/>
  <text x="109" y="78" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" font-weight="600" fill="#bed0e4" text-anchor="middle" letter-spacing="0.5">Contributions</text>
  <text x="109" y="104" font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="28" font-weight="700" fill="#f0f1f2" text-anchor="middle">${warCommits}</text>
  <text x="320" y="78" font-family="'Segoe UI', system-ui, sans-serif" font-size="10" font-weight="600" fill="#bed0e4" text-anchor="middle" letter-spacing="0.5">Shelter time (war)</text>
  <text x="320" y="104" font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="22" font-weight="700" fill="#f0f1f2" text-anchor="middle">${formatDuration(sWar)}</text>
</svg>`;
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  const pathParts = url.pathname.split("/");
  let token = pathParts[pathParts.length - 1] || "";
  token = token.replace(/\.svg$/, "");

  if (!token) {
    return new Response("Missing token", { status: 400 });
  }

  const isWar = url.searchParams.get("war") === "1";

  const supabase = createClient(supabaseUrl, supabaseKey);

  const { data: badge } = await supabase
    .from("badges")
    .select("area_name")
    .eq("token", token)
    .single();

  if (!badge) {
    return new Response("Badge not found", { status: 404 });
  }

  let s24h = 0, s7d = 0, s30d = 0, sWar = 0;
  const { data: areaData } = await supabase
    .from("area_times")
    .select("s_24h, s_7d, s_30d, s_war")
    .eq("area_name", badge.area_name)
    .single();

  if (areaData) {
    s24h = areaData.s_24h;
    s7d = areaData.s_7d;
    s30d = areaData.s_30d;
    sWar = areaData.s_war ?? 0;
  }

  let commits = 0, warCommits = 0;
  const { data: cacheData } = await supabase
    .from("badge_data_cache")
    .select("commits, war_commits")
    .eq("token", token)
    .single();

  if (cacheData) {
    commits = cacheData.commits || 0;
    warCommits = cacheData.war_commits || 0;
  }

  const svg = isWar
    ? generateWarBadge(sWar, warCommits)
    : generateBadge(s24h, s7d, s30d, commits);

  return new Response(svg, {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=900, s-maxage=900",
      "Access-Control-Allow-Origin": "*",
    },
  });
});

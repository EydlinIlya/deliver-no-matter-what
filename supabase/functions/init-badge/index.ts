import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const ghPat = Deno.env.get("GH_PAT") || "";

async function fetchGitHubContributions(
  login: string,
): Promise<number> {
  if (!ghPat) return 0;
  const now = new Date();
  const from = new Date(now.getTime() - 30 * 86400_000);
  const query = JSON.stringify({
    query: `{ user(login: "${login}") {
      contributionsCollection(from: "${from.toISOString()}", to: "${now.toISOString()}") {
        contributionCalendar { totalContributions }
      }
    } }`,
  });

  const resp = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${ghPat}`,
      "Content-Type": "application/json",
      "User-Agent": "deliver-no-matter-what/0.1",
    },
    body: query,
  });

  if (!resp.ok) return 0;
  const data = await resp.json();
  try {
    return data.data.user.contributionsCollection.contributionCalendar
      .totalContributions;
  } catch {
    return 0;
  }
}

Deno.serve(async (req) => {
  // CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      },
    });
  }

  const { token } = await req.json();
  if (!token) {
    return new Response(JSON.stringify({ error: "Missing token" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const supabase = createClient(supabaseUrl, supabaseKey);

  // Look up badge (only need github_login — no token stored)
  const { data: badge } = await supabase
    .from("badges")
    .select("github_login")
    .eq("token", token)
    .single();

  if (!badge) {
    return new Response(JSON.stringify({ error: "Badge not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Fetch contributions using bot PAT
  let commits = 0;
  if (badge.github_login) {
    commits = await fetchGitHubContributions(badge.github_login);
  }

  // Store in badge_data_cache
  await supabase.from("badge_data_cache").upsert({
    token,
    data: JSON.stringify([0, 0, 0, commits]),
    updated_at: new Date().toISOString(),
  });

  return new Response(JSON.stringify({ commits }), {
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
});

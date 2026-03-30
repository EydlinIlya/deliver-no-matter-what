-- RLS policies for Vercel static site + Supabase Auth

-- badges: users can only manage their own
ALTER TABLE badges ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users manage own badges" ON badges;
CREATE POLICY "Users manage own badges" ON badges
    FOR ALL
    USING (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- badge_data_cache: public read (Edge Function uses service key, but anon needs read for previews)
ALTER TABLE badge_data_cache ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read badge_data_cache" ON badge_data_cache;
CREATE POLICY "Public read badge_data_cache" ON badge_data_cache
    FOR SELECT USING (true);

-- csv_cache: no client access needed (only GH Actions via service key)
ALTER TABLE csv_cache ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service only csv_cache" ON csv_cache;
-- No policies = no client access (service key bypasses RLS)

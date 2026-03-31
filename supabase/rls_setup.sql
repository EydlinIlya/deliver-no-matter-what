-- RLS policies for Vercel static site + Supabase Auth

-- badges: users can only manage their own
-- FK: badges.user_id → auth.users(id) ON DELETE CASCADE
ALTER TABLE badges ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users manage own badges" ON badges;
CREATE POLICY "Users manage own badges" ON badges
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- badge_data_cache: public read, cascade-deleted with badge
-- FK: badge_data_cache.token → badges(token) ON DELETE CASCADE
ALTER TABLE badge_data_cache ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read badge_data_cache" ON badge_data_cache;
CREATE POLICY "Public read badge_data_cache" ON badge_data_cache
    FOR SELECT USING (true);

-- area_times: public read (everyone can see shelter times per area)
ALTER TABLE area_times ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read area_times" ON area_times;
CREATE POLICY "Public read area_times" ON area_times
    FOR SELECT USING (true);

-- csv_cache: no client access needed (only GH Actions via direct PG / service_role)
-- RLS enabled with deny-all policy to silence Supabase linter
ALTER TABLE csv_cache ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Deny all client access" ON csv_cache;
CREATE POLICY "Deny all client access" ON csv_cache
    FOR ALL USING (false);

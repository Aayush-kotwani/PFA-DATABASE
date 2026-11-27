-- ============================================================================
-- Read-Only PostgreSQL Role for BI & ML Analytics Tools
-- (pandas, Metabase, Power BI, Superset, etc.)
--
-- NEVER use the main application credentials for external analysis tools.
-- Run these statements in Neon Console -> SQL Editor with your target database
-- selected (e.g. pfa-dog-sterilization-db).
-- ============================================================================

-- 1. Create a dedicated login role with a strong password
--    (Replace 'CHANGE_ME_STRONG_READONLY_PASSWORD' before executing!)
CREATE ROLE analytics_reader WITH LOGIN PASSWORD 'CHANGE_ME_STRONG_READONLY_PASSWORD';

-- 2. Allow connecting to the database and viewing the public schema
GRANT CONNECT ON DATABASE "pfa-dog-sterilization-db" TO analytics_reader;
GRANT USAGE ON SCHEMA public TO analytics_reader;

-- 3. Grant SELECT-only access to all existing tables (no INSERT/UPDATE/DELETE)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_reader;

-- 4. Automatically grant SELECT on any future tables created by migrations
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO analytics_reader;

-- Optional: Verify permissions
-- SELECT grantee, table_name, privilege_type
-- FROM information_schema.role_table_grants
-- WHERE grantee = 'analytics_reader';

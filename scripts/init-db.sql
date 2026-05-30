-- =============================================================
-- SplitEase Database Initialization
-- Run automatically by PostgreSQL on first container start.
-- Alembic migrations (run per-service) create the actual tables.
-- =============================================================

-- Create schemas so migrations can target them immediately
CREATE SCHEMA IF NOT EXISTS auth_schema;
CREATE SCHEMA IF NOT EXISTS expenses_schema;

-- Verify schemas were created
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('auth_schema', 'expenses_schema');

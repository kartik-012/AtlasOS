-- ==============================================================================
-- AtlasOS PostgreSQL Initialization Script
--
-- Runs ONCE on first container initialization (via /docker-entrypoint-initdb.d/).
-- Creates required extensions and the restricted application role.
--
-- Why extensions:
--   uuid-ossp:  Provides uuid_generate_v4() for server-side UUID generation.
--               This is preferred over client-side generation because it ensures
--               IDs are generated atomically within the database transaction.
--   pgcrypto:   Provides gen_random_bytes() and crypt() for cryptographic
--               operations at the database level (backup hashing scenarios).
-- ==============================================================================

-- Enable UUID generation support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- Application Role (for production use with RLS)
--
-- In production, the application connects as 'app_user' with restricted
-- privileges. The superuser 'atlas' (created by POSTGRES_USER env var) is
-- used only for migrations and administrative tasks.
--
-- In development, we use the 'atlas' superuser directly for simplicity,
-- but RLS policies are still created and tested.
-- ==============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user'
    ) THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_user_secret';
    END IF;
END
$$;

-- Grant the app_user connect and schema usage rights.
-- Table-level grants are applied after Alembic creates the tables.
GRANT CONNECT ON DATABASE atlasos TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;

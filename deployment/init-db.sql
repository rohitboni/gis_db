-- Initialize PostGIS extensions
-- This script runs automatically when the database is first created

-- Connect to the gis_db database
\c gis_db;

-- Create PostGIS extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE gis_db TO postgres;

-- Show installed extensions
SELECT extname, extversion FROM pg_extension WHERE extname LIKE '%postgis%';

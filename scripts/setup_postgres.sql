-- Lansdowne — PostgreSQL setup (run as superuser postgres)

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lansdowne') THEN
    CREATE ROLE lansdowne WITH LOGIN PASSWORD 'lansdowne';
  ELSE
    ALTER ROLE lansdowne WITH LOGIN PASSWORD 'lansdowne';
  END IF;
END
$$;

SELECT 'CREATE DATABASE lansdowne OWNER lansdowne'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'lansdowne')\gexec

GRANT ALL PRIVILEGES ON DATABASE lansdowne TO lansdowne;

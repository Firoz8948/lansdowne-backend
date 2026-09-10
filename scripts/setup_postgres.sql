-- ChaklaDekho — PostgreSQL setup (run as superuser postgres)

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'chakladkho') THEN
    CREATE ROLE chakladkho WITH LOGIN PASSWORD 'chakladkho';
  ELSE
    ALTER ROLE chakladkho WITH LOGIN PASSWORD 'chakladkho';
  END IF;
END
$$;

SELECT 'CREATE DATABASE chakladkho OWNER chakladkho'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'chakladkho')\gexec

GRANT ALL PRIVILEGES ON DATABASE chakladkho TO chakladkho;

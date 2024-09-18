-- Create a group
CREATE ROLE meshdb_ro;

-- Grant access to existing tables
GRANT USAGE ON SCHEMA public TO meshdb_ro;

DO
$$
BEGIN
EXECUTE (
   SELECT 'GRANT ALL ON TABLE '
       || string_agg (format('%I.%I', table_schema, table_name), ',')
       || ' TO meshdb_ro'
   FROM   information_schema.tables
   WHERE  table_schema = 'public'
   AND    table_name LIKE 'meshapi\_%'
   AND    table_name NOT LIKE '(%\_seq|%celeryserializerhook%)'
   );
END
$$;

-- Grant access to future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO meshdb_ro;

-- Create a final user with password
CREATE USER meshdb_ro WITH PASSWORD 'secret';
ALTER USER meshdb_ro WITH PASSWORD 'secret';
GRANT meshdb_ro TO meshdb_ro;

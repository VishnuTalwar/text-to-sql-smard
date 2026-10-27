-- Creates the read-only role used by the grader (and later, the agent).
-- SELECT-only on the three data tables; no INSERT/UPDATE/DELETE/DDL.
-- See DECISIONS.md D2/D8 and open item O11.
--
-- Run with the password passed in as a psql variable, so the secret never
-- lives in this file (matches GRADER_DB_PASSWORD in .env). Feed the file in on
-- stdin: with `docker exec ... -f`, psql would look for the file inside the container.
--   docker exec -i text-to-sql-db psql -U app -d smard \
--     -v grader_password="<password from .env>" < sql/create_grader_role.sql
-- Pass the password as is, without extra quotes: the script quotes it itself.
-- Safe to re-run: the role is only created if it does not exist yet.

-- psql does not substitute variables inside a DO $$ ... $$ block, so the CREATE ROLE
-- statement is built by a query and run with \gexec (no row = role exists, nothing to run).
SELECT format('CREATE ROLE grader_ro WITH LOGIN PASSWORD %L', :'grader_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'grader_ro')
\gexec

GRANT CONNECT ON DATABASE smard TO grader_ro;
GRANT USAGE ON SCHEMA public TO grader_ro;
GRANT SELECT ON erzeugung, verbrauch, preise TO grader_ro;

-- Any future table created by the loader account (app) is automatically
-- readable by grader_ro too, without a manual GRANT each time.
ALTER DEFAULT PRIVILEGES FOR ROLE app IN SCHEMA public GRANT SELECT ON TABLES TO grader_ro;

-- Defence in depth: even a legitimate SELECT can't hang the connection.
ALTER ROLE grader_ro SET statement_timeout = '30s';

-- No temporary tables either. PostgreSQL grants TEMP to PUBLIC by default, so the
-- revoke from PUBLIC is what takes effect; the one from grader_ro is explicit
-- documentation. PUBLIC keeps CONNECT. The loader account (app) holds its own TEMP
-- grant and is unaffected.
REVOKE TEMP ON DATABASE smard FROM PUBLIC;
REVOKE TEMP ON DATABASE smard FROM grader_ro;

-- HUG-252 — Cloud SQL initial schema setup.
-- Run by infra/setup.sh once per environment as cubi_migrate (DB owner).
-- Idempotent: safe to re-run.

-- Required by the agent's vector search (HUG-191 / HUG-192).
CREATE EXTENSION IF NOT EXISTS vector;

-- cubi_runtime reads application data and writes ONLY audit_log.
-- (CLAUDE.md invariant: "All SQL execution is read-only at the DB role level."
-- The single permitted exception is audit_log, granted in bootstrap.sh after
-- the migration that creates the table has run — see HUG-253.)

GRANT USAGE ON SCHEMA public TO cubi_runtime;

-- Default privileges: tables created later by cubi_migrate (i.e., by the
-- HUG-253 migrations) will automatically grant SELECT to cubi_runtime.
ALTER DEFAULT PRIVILEGES FOR ROLE cubi_migrate IN SCHEMA public
  GRANT SELECT ON TABLES TO cubi_runtime;

-- Sequences (id generators) need USAGE so SELECT-ing a serial column works
-- through joins. SELECT (read currval) is enough; UPDATE (nextval) is denied.
ALTER DEFAULT PRIVILEGES FOR ROLE cubi_migrate IN SCHEMA public
  GRANT SELECT ON SEQUENCES TO cubi_runtime;

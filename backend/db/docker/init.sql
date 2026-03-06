-- Create the application role as a regular (non-superuser) user.
-- FORCE ROW LEVEL SECURITY only works correctly on non-superuser roles.
CREATE ROLE axiom WITH LOGIN PASSWORD 'axiom' CREATEDB CREATEROLE;
GRANT ALL PRIVILEGES ON DATABASE axiom_dev TO axiom;
GRANT CREATE ON SCHEMA public TO axiom;

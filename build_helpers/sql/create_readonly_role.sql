-- sql/create_readonly_role.sql

CREATE ROLE schemalens_reader WITH LOGIN PASSWORD 'replace-with-a-strong-password';

GRANT CONNECT ON DATABASE schemalens TO schemalens_reader;

GRANT USAGE ON SCHEMA public TO schemalens_reader;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO schemalens_reader;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO schemalens_reader;
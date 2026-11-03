"""Independent PostgreSQL journal for the explicitly limited contact pilot."""

from contextlib import contextmanager
import json
import os
import re
import time
import uuid


class PilotError(Exception):
    """Only static, safe error codes belong in this exception."""

    def __init__(self, code, diagnostics=None):
        super().__init__(code)
        self.diagnostics = diagnostics or {}


def connection_failure(exc):
    """Inspect libpq's response but return allowlisted labels, never raw text."""
    state = getattr(exc, "sqlstate", None)
    state = state if isinstance(state, str) and re.fullmatch(r"[A-Z0-9]{5}", state) else None
    message = str(exc).lower()
    if state == "28P01" or "password authentication failed" in message:
        code = "journal_authentication_failed"
    elif state == "3D000" or ("database" in message and "does not exist" in message):
        code = "journal_database_missing"
    elif state == "28000" or "no pg_hba.conf entry" in message:
        code = "journal_access_denied"
    elif "ssl" in message or "certificate verify failed" in message:
        code = "journal_tls_error"
    elif "could not translate host name" in message:
        code = "journal_host_resolution_failed"
    elif "timeout expired" in message or "connection timed out" in message:
        code = "journal_connection_timeout"
    elif state == "57P03" or any(text in message for text in (
            "connection refused", "server closed the connection unexpectedly",
            "database system is starting up", "connection reset")):
        code = "journal_not_ready"
    else:
        code = "journal_connection_failed"
    name = type(exc).__name__
    name = name if re.fullmatch(r"[A-Za-z0-9_]{1,64}", name) else "Error"
    return code, {"exception_type": name, "sqlstate": state}


DDL = """
CREATE SCHEMA IF NOT EXISTS bambus_pilot;
CREATE TABLE IF NOT EXISTS bambus_pilot.version (version integer PRIMARY KEY CHECK (version = 1));
INSERT INTO bambus_pilot.version VALUES (1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS bambus_pilot.runs (
    id uuid PRIMARY KEY, namespace text NOT NULL, operation text NOT NULL,
    source_identity text NOT NULL, target_identity text NOT NULL,
    mapping_version text NOT NULL, state text NOT NULL DEFAULT 'running',
    source_id bigint, target_id bigint, payload_digest text,
    error_code text, started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz
);
CREATE TABLE IF NOT EXISTS bambus_pilot.events (
    id bigserial PRIMARY KEY, run_id uuid NOT NULL REFERENCES bambus_pilot.runs(id),
    state text NOT NULL, details jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS bambus_pilot.mappings (
    namespace text PRIMARY KEY, source_model text NOT NULL CHECK (source_model = 'res.partner'),
    source_id bigint NOT NULL, target_model text NOT NULL CHECK (target_model = 'res.partner'),
    target_id bigint NOT NULL, marker text NOT NULL, mapping_version text NOT NULL,
    payload_digest text NOT NULL, last_run uuid NOT NULL REFERENCES bambus_pilot.runs(id),
    state text NOT NULL CHECK (state = 'reconciled'), updated_at timestamptz NOT NULL DEFAULT now()
);
"""


class Journal:
    def __init__(self, connection):
        self.connection = connection

    @classmethod
    def from_environment(cls):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError:
            raise PilotError("install_pilot_requirements") from None
        if not os.environ.get("JOURNAL_DB_PASSWORD"):
            raise PilotError("missing_JOURNAL_DB_PASSWORD")
        if os.environ.get("JOURNAL_DB_HOST", "127.0.0.1") not in {"127.0.0.1", "localhost", "::1"}:
            raise PilotError("pilot_journal_requires_loopback")
        host = os.environ.get("JOURNAL_DB_HOST", "127.0.0.1")
        try:
            port = int(os.environ.get("JOURNAL_DB_PORT", "55432"))
            if not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            raise PilotError("invalid_JOURNAL_DB_PORT") from None
        for attempt in range(3):
            connection = None
            try:
                connection = psycopg.connect(
                    host=host, port=port,
                    dbname="bambus_migration_journal", user="bambus_journal",
                    password=os.environ["JOURNAL_DB_PASSWORD"], connect_timeout=5,
                    autocommit=True, row_factory=dict_row,
                )
                if connection.execute("SELECT current_database() AS name").fetchone()["name"] != "bambus_migration_journal":
                    raise PilotError("journal_database_must_be_independent")
                return cls(connection)
            except Exception as exc:
                if connection is not None:
                    connection.close()
                if isinstance(exc, PilotError):
                    raise
                code, diagnostics = connection_failure(exc)
                diagnostics.update(host=host, port=port, attempts=attempt + 1)
                if attempt < 2 and code in {"journal_not_ready", "journal_connection_timeout"}:
                    time.sleep(1)
                    continue
                raise PilotError(code, diagnostics) from None

    def initialize(self):
        with self.connection.transaction():
            self.connection.execute(DDL)

    @contextmanager
    def lock(self, namespace):
        key = int.from_bytes(bytes.fromhex(namespace)[:8], "big", signed=True)
        row = self.connection.execute("SELECT pg_try_advisory_lock(%s) AS acquired", (key,)).fetchone()
        if not row["acquired"]:
            raise PilotError("pilot_busy")
        try:
            yield
        finally:
            if not self.connection.closed:
                self.connection.execute("SELECT pg_advisory_unlock(%s)", (key,))

    def start(self, namespace, operation, source_identity, target_identity, version):
        run_id = str(uuid.uuid4())
        self.connection.execute(
            "INSERT INTO bambus_pilot.runs (id,namespace,operation,source_identity,target_identity,mapping_version) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (run_id, namespace, operation, source_identity, target_identity, version),
        )
        self.event(run_id, "pending")
        return run_id

    def event(self, run_id, state, **details):
        self.connection.execute(
            "INSERT INTO bambus_pilot.events (run_id,state,details) VALUES (%s,%s,%s::jsonb)",
            (run_id, state, json.dumps(details)),
        )

    def mapping(self, namespace):
        return self.connection.execute("SELECT * FROM bambus_pilot.mappings WHERE namespace=%s", (namespace,)).fetchone()

    def has_intent(self, namespace, state, operation=None):
        row = self.connection.execute(
            "SELECT EXISTS (SELECT 1 FROM bambus_pilot.events e JOIN bambus_pilot.runs r ON r.id=e.run_id "
            "WHERE r.namespace=%s AND e.state=%s AND (%s::text IS NULL OR e.details->>'operation'=%s)) AS found",
            (namespace, state, operation, operation),
        ).fetchone()
        return row["found"]

    def finish(self, run_id, state, source_id=None, target_id=None, digest=None, error=None):
        self.connection.execute(
            "UPDATE bambus_pilot.runs SET state=%s,source_id=%s,target_id=%s,payload_digest=%s,error_code=%s,finished_at=now() WHERE id=%s",
            (state, source_id, target_id, digest, error, run_id),
        )

    def reconciled(self, namespace, run_id, source_id, target_id, marker, version, digest):
        with self.connection.transaction():
            self.connection.execute(
                "INSERT INTO bambus_pilot.mappings "
                "(namespace,source_model,source_id,target_model,target_id,marker,mapping_version,payload_digest,last_run,state) "
                "VALUES (%s,'res.partner',%s,'res.partner',%s,%s,%s,%s,%s,'reconciled') "
                "ON CONFLICT (namespace) DO UPDATE SET target_id=EXCLUDED.target_id,payload_digest=EXCLUDED.payload_digest,"
                "last_run=EXCLUDED.last_run,state='reconciled',updated_at=now()",
                (namespace, source_id, target_id, marker, version, digest, run_id),
            )
            self.event(run_id, "reconciled")
            self.finish(run_id, "reconciled", source_id, target_id, digest)

    def status(self, namespace):
        rows = self.connection.execute(
            "SELECT id::text,operation,state,source_id,target_id,error_code,started_at::text,finished_at::text "
            "FROM bambus_pilot.runs WHERE namespace=%s ORDER BY started_at DESC LIMIT 100", (namespace,)
        ).fetchall()
        return {"latest_run_state": rows[0]["state"] if rows else "no_runs",
                "runs": rows, "mapping": self.mapping(namespace)}

    def close(self):
        self.connection.close()

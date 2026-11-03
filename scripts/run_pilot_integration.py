"""Run real PostgreSQL + synthetic HTTP integration tests in an owned container.

Requires Docker and requirements-pilot.txt. Never connects to existing databases.
The owned ephemeral test container is removed on exit; no named volumes are used.
"""

import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import unittest

IMAGE = "postgres:16@sha256:5db6dac2ef5dcff512f4f00a009c3c332b9f2f28f24277175bf3e4a3d02ef83a"


def main():
    import psycopg
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "integration_tests"))
    docker_env = {key: value for key, value in os.environ.items() if key not in {
        "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"}}
    docker_env["POSTGRES_PASSWORD"] = secrets.token_urlsafe(32)
    command = ["docker", "--host=unix:///var/run/docker.sock"]
    container = "bambus-pilot-test-" + secrets.token_hex(6)

    def docker(*args):
        result = subprocess.run(command + list(args), env=docker_env, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("Isolated test Docker operation failed; no existing database was modified")
        return result.stdout.strip()

    try:
        docker("run", "--detach", "--name", container, "--memory=256m",
               "--tmpfs", "/var/lib/postgresql/data:rw,size=128m", "--publish", "127.0.0.1::5432",
               "--env", "POSTGRES_PASSWORD", "--env", "POSTGRES_USER=bambus_journal",
               "--env", "POSTGRES_DB=bambus_migration_journal", IMAGE)
        port = docker("port", container, "5432/tcp").rsplit(":", 1)[1]
        os.environ.update(JOURNAL_DB_HOST="127.0.0.1", JOURNAL_DB_PORT=port,
                          JOURNAL_DB_PASSWORD=docker_env["POSTGRES_PASSWORD"])
        deadline = time.monotonic() + 45
        while True:
            try:
                with psycopg.connect(host="127.0.0.1", port=port, dbname="bambus_migration_journal",
                                     user="bambus_journal", password=docker_env["POSTGRES_PASSWORD"], connect_timeout=1):
                    break
            except psycopg.OperationalError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Isolated PostgreSQL startup timed out") from None
                time.sleep(0.5)
        suite = unittest.defaultTestLoader.loadTestsFromName("test_pilot_pg")
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() and result.testsRun else 1
    finally:
        # Exact owned test container only. No user lab service or named volume.
        subprocess.run(command + ["rm", "--force", container], env=docker_env, capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())

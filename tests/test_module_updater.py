import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from scripts import update_odoo_module as updater


class FakeCommands:
    def __init__(self, fail=None, dirty=False, running=True, branch="development", healthy=True):
        self.calls, self.fail, self.dirty, self.running = [], fail, dirty, running
        self.branch, self.healthy = branch, healthy

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        if self.fail and self.fail(command):
            raise updater.UpdateError("Synthetic command failure")
        if command[:3] == ["git", "branch", "--show-current"]:
            return self.branch
        if command[:3] == ["git", "status", "--porcelain"]:
            return " M addons/local.py" if self.dirty else ""
        if "inspect" in command:
            return ("true" if self.running else "false") if "{{.State.Running}}" in command else "healthy" if self.healthy else "starting"
        return ""


class TestModuleUpdater(unittest.TestCase):
    def preflight(self, state="installed", manifest_version="20.0.1.0.0"):
        pg = MagicMock()
        connection = pg.connect.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [("synthetic_module", state)]
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory) / "synthetic_module"
            module.mkdir()
            (module / "__manifest__.py").write_text(repr({"version": manifest_version}))
            payload = [20, "odoo20_migration", "pg20", [directory], ["synthetic_module"]]
            with patch.dict(sys.modules, {"odoo": SimpleNamespace(release=SimpleNamespace(version_info=[20])), "psycopg2": pg}):
                with patch.object(sys, "argv", ["-c", json.dumps(payload)]), contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(updater.PREFLIGHT, "container-preflight", "exec"), {})
        return connection, cursor

    def test_container_preflight_queries_installed_state_read_only(self):
        connection, cursor = self.preflight()
        connection.set_session.assert_called_once_with(readonly=True)
        self.assertTrue(cursor.execute.call_args.args[0].startswith("SELECT "))
        with self.assertRaises(SystemExit):
            self.preflight(state="uninstalled")

    def test_container_preflight_rejects_explicit_wrong_major_manifest(self):
        with self.assertRaises(SystemExit):
            self.preflight(manifest_version="12.0.1.0.0")

    def perform(self, fake, version=20, pull=True):
        with contextlib.redirect_stdout(io.StringIO()):
            updater.update(Path("."), version, ["synthetic_module"], pull, fake)

    def test_success_pulls_upgrades_then_restarts_only_selected_app(self):
        fake = FakeCommands()
        self.perform(fake)
        pull = next(i for i,c in enumerate(fake.calls) if c[:2] == ["git", "pull"])
        upgrade = next(i for i,c in enumerate(fake.calls) if "--update=synthetic_module" in c)
        restart = next(i for i,c in enumerate(fake.calls) if "restart" in c)
        self.assertLess(pull, upgrade)
        self.assertLess(upgrade, restart)
        self.assertEqual(fake.calls[restart][-1], updater.LABS[20]["container"])
        self.assertTrue(all("--db_password" not in " ".join(c) for c in fake.calls))

    def test_dirty_checkout_and_stopped_app_block_before_pull(self):
        for fake in (FakeCommands(dirty=True), FakeCommands(running=False), FakeCommands(branch="main"), FakeCommands(healthy=False)):
            with self.assertRaises(updater.UpdateError):
                self.perform(fake)
            self.assertFalse(any(c[:2] == ["git", "pull"] or "restart" in c for c in fake.calls))

    def test_pull_failure_never_runs_preflight_upgrade_or_restart(self):
        fake = FakeCommands(fail=lambda c: c[:2] == ["git", "pull"])
        with self.assertRaises(updater.UpdateError):
            self.perform(fake)
        self.assertFalse(any("exec" in c or "restart" in c for c in fake.calls))

    def test_preflight_or_upgrade_failure_never_restarts(self):
        for condition in (lambda c: "-c" in c, lambda c: "--update=synthetic_module" in c):
            fake = FakeCommands(fail=condition)
            with self.assertRaises(updater.UpdateError):
                self.perform(fake)
            self.assertFalse(any("restart" in c for c in fake.calls))

    def test_skip_pull_allows_local_development_edits(self):
        fake = FakeCommands(dirty=True)
        self.perform(fake, pull=False)
        self.assertFalse(any(c[:2] in (["git", "pull"], ["git", "status"]) for c in fake.calls))
        self.assertTrue(any("restart" in c for c in fake.calls))

    def test_version12_uses_only_its_database_container_and_paths(self):
        command = updater.upgrade_command(12, ["synthetic_module"])
        self.assertIn("--database=odoo12_demo", command)
        self.assertIn(updater.LABS[12]["container"], command)
        self.assertNotIn("/mnt/bambus-addons", " ".join(command))
        self.assertNotIn("odoo20_migration", " ".join(command))

    def test_module_scope_and_dry_run_have_no_side_effects(self):
        self.assertEqual(updater.modules_from(["first,second"]), ["first", "second"])
        for values in (["all"], ["first", "first"], ["module;command"], ["../module"]):
            with self.assertRaises(updater.UpdateError):
                updater.modules_from(values)
        with patch.object(updater, "update") as update, patch.object(updater, "wait_ready") as ready:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(updater.main(["--modules", "synthetic_module", "--dry-run"]), 0)
            update.assert_not_called()
            ready.assert_not_called()

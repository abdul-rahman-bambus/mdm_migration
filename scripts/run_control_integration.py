"""Install/test the addon on real Odoo 20, import a real journal and test its UI.

Owns disposable containers/network/tmpfs only; never uses an existing lab DB.
Needs Docker, Chromium and requirements-control-test.txt. Artifacts are ignored.
"""

import json
import io
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tarfile
import time
import urllib.request

PG_IMAGE = "postgres:16@sha256:5db6dac2ef5dcff512f4f00a009c3c332b9f2f28f24277175bf3e4a3d02ef83a"
ODOO_IMAGE = "odoo:20@sha256:a97a7665e2b9fd890e12785491a2c91d779f800bcbc30873dada1c8748b28f1c"


def main():
    import psycopg
    from playwright.sync_api import sync_playwright
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root), str(root / "integration_tests")]
    from migration_lab.journal import Journal
    from migration_lab.monitor import MirrorClient, transfer
    from migration_lab.pilot import PartnerAPI, migrate, specification
    from migration_lab.preflight import ProbeFailure, Settings
    from test_pilot_pg import RPCPartnerFixture

    output = root / "reports/control-integration"
    output.mkdir(parents=True, exist_ok=True)
    docker_env = {k: v for k, v in os.environ.items() if k not in {
        "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"}}
    password, admin_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    docker_env.update(POSTGRES_PASSWORD=password, PGPASSWORD=password, MONITOR_TEST_PASSWORD=admin_password)
    base = ["docker", "--host=unix:///var/run/docker.sock"]
    suffix = secrets.token_hex(6)
    network, pg, app = [f"bambus-control-{name}-{suffix}" for name in ("net", "pg", "app")]
    journal = None
    # A pinned public predecessor tests a real stored-field upgrade rather than
    # assuming that fresh installation proves existing receipts remain valid.
    previous = output / ("previous-addon-" + suffix)
    archive = subprocess.run(["git", "archive", "935c53e", "addons/bambus_migration_control"],
                             cwd=root, capture_output=True)
    if archive.returncode:
        raise RuntimeError("Upgrade validation needs public commit 935c53e in the local Git history")
    previous.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as source_archive:
        source_archive.extractall(previous, filter="data")
    # data-filtered archive directories inherit the host's restrictive umask;
    # this pinned public source must be readable by Odoo's container user.
    previous.chmod(0o755)
    for entry in previous.rglob("*"):
        entry.chmod(0o755 if entry.is_dir() else 0o644)

    def redact(value):
        return value.replace(password, "[redacted]").replace(admin_password, "[redacted]")

    def docker(*args, input=None, log=None, timeout=600):
        result = subprocess.run(base + list(args), input=input, env=docker_env, capture_output=True, text=True, timeout=timeout)
        text = redact(result.stdout + result.stderr)
        if log:
            (output / log).write_text(text)
        if result.returncode:
            print(text[-5000:])
            raise RuntimeError("Owned Odoo test operation failed")
        return result.stdout

    def wait_database(port):
        deadline = time.monotonic() + 45
        while True:
            try:
                return psycopg.connect(host="127.0.0.1", port=port, dbname="bambus_migration_journal",
                                        user="bambus_journal", password=password, autocommit=True, connect_timeout=1)
            except psycopg.OperationalError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Owned PostgreSQL startup timed out") from None
                time.sleep(0.5)

    try:
        docker("network", "create", network)
        docker("run", "--detach", "--name", pg, "--network", network, "--memory=1g",
               "--tmpfs", "/var/lib/postgresql/data:rw,size=512m", "--publish", "127.0.0.1::5432",
               "--env", "POSTGRES_PASSWORD", "--env", "POSTGRES_USER=bambus_journal",
               "--env", "POSTGRES_DB=bambus_migration_journal", PG_IMAGE)
        port = docker("port", pg, "5432/tcp").strip().rsplit(":", 1)[1]
        with wait_database(port) as connection:
            connection.execute("CREATE DATABASE odoo20_migration OWNER bambus_journal")
        os.environ.update(JOURNAL_DB_HOST="127.0.0.1", JOURNAL_DB_PORT=port, JOURNAL_DB_PASSWORD=password)
        journal = Journal.from_environment()
        journal.initialize()
        docker("run", "--detach", "--name", app, "--network", network, "--memory=2g",
               "--publish", "127.0.0.1::8069", "--tmpfs", "/var/lib/odoo:rw,size=256m,mode=1777",
               "--mount", f"type=bind,src={root / 'addons'},dst=/mnt/extra-addons,readonly",
               "--mount", f"type=bind,src={previous / 'addons'},dst=/mnt/previous-addons,readonly",
               "--env", "PGPASSWORD", "--env", "MONITOR_TEST_PASSWORD", "--entrypoint", "sleep", ODOO_IMAGE, "infinity")
        odoo = ["odoo", "--config=/dev/null", "--db_host=" + pg, "--db_user=bambus_journal",
                "--database=odoo20_migration", "--addons-path=/mnt/extra-addons", "--data-dir=/var/lib/odoo"]
        old_odoo = [arg.replace("--addons-path=/mnt/extra-addons", "--addons-path=/mnt/previous-addons") for arg in odoo]
        print("Installing previous addon and preserving a real native-mode history receipt...", flush=True)
        docker("exec", app, *old_odoo, "--init=bambus_migration_control", "--without-demo=all", "--stop-after-init", "--no-http", log="previous-install.log")
        legacy_shell = """import json
admin = env.ref('base.user_admin')
admin.write({'group_ids': [(4, env.ref('bambus_migration_control.group_contact_trial').id)]})
data = {'version': 'contact-history-v1', 'source_id': 900001,
        'values': {'name': 'Synthetic pre-upgrade contact', 'email': 'pre-upgrade@example.invalid', 'phone': '+12025550150', 'is_company': False, 'active': True, 'vat': '', 'country_code': ''},
        'messages': [{'id': 800001, 'date': '2019-10-01 09:30:00', 'author': 'Synthetic historical author', 'subject': 'Before upgrade', 'body': '<p>Existing history</p>', 'kind': 'comment', 'subtype': 'Note', 'changes': [], 'attachments': [700001]}],
        'attachments': [{'id': 700001, 'name': 'pre-upgrade.txt', 'data': 'dHJpYWw='}]}
result = env['res.partner'].with_user(admin).bambus_trial_apply(data)
with open('/var/lib/odoo/legacy-trial.json', 'w') as output:
    json.dump({'data': data, 'result': result}, output)
env.cr.commit()
"""
        docker("exec", "--interactive", app, "odoo", "shell", *old_odoo[1:], "--no-http", input=legacy_shell, log="previous-bootstrap.log")
        print("Upgrading stored fields and running native Odoo model/view/security tests...", flush=True)
        docker("exec", app, *odoo, "--update=bambus_migration_control", "--without-demo=all",
                     "--test-enable", "--test-tags=/bambus_migration_control", "--stop-after-init", "--no-http", log="odoo-install.log")
        # docker returns stdout; Odoo uses stderr. Inspect the redacted combined
        # log and require a positive, successful current-run test count.
        summaries = re.findall(r"(\d+) failed, (\d+) error\(s\) of (\d+) tests", (output / "odoo-install.log").read_text())
        assert summaries and int(summaries[-1][2]) >= 14 and summaries[-1][:2] == ("0", "0"), "Native addon tests did not pass; inspect the current install log"
        print("Native addon tests:", summaries[-1], flush=True)
        upgrade_check = """import json
with open('/var/lib/odoo/legacy-trial.json') as source:
    legacy = json.load(source)
admin = env.ref('base.user_admin')
partner = env['res.partner'].browse(legacy['result']['target_id'])
assert partner.bambus_legacy_classification == 'native' and not partner.is_company
result = env['res.partner'].with_user(admin).bambus_trial_preview(legacy['data'], partner.id, legacy['result']['items'])
assert result['operation'] == 'no_change' and result['items'] == legacy['result']['items']
"""
        docker("exec", "--interactive", app, "odoo", "shell", *odoo[1:], "--no-http", input=upgrade_check, log="upgrade-check.log")
        print("Previous contact, history/file identities and receipt fingerprints survived the addon upgrade.", flush=True)
        shell = """import os
admin = env.ref('base.user_admin')
admin.with_context(no_reset_password=True).write({'password': os.environ['MONITOR_TEST_PASSWORD'], 'group_ids': [(4, env.ref('bambus_migration_control.group_migration_importer').id)]})
env.cr.commit()
"""
        docker("exec", "--interactive", app, "odoo", "shell", *odoo[1:], "--no-http", input=shell, log="odoo-bootstrap.log")
        docker("exec", "--detach", app, *odoo, "--http-interface=0.0.0.0", "--http-port=8069", "--workers=0", "--logfile=/var/lib/odoo/http.log")
        http_port = docker("port", app, "8069/tcp").strip().rsplit(":", 1)[1]
        url = "http://127.0.0.1:" + http_port
        deadline = time.monotonic() + 60
        while True:
            try:
                with urllib.request.urlopen(url + "/web/login?db=odoo20_migration", timeout=2) as response:
                    if response.status == 200:
                        break
            except Exception:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Owned Odoo HTTP startup timed out") from None
                time.sleep(0.5)
        settings = Settings(url, "odoo20_migration", "admin", admin_password)
        target = PartnerAPI(settings, 20, writable=True)
        with RPCPartnerFixture(12) as source:
            spec = specification("ui-smoke", "fixture-source", "fixture-target")

            def pilot(action="sync", apply=False, phone=None):
                return migrate(source.api, target, journal, spec, "fixture-source", "fixture-target", action, apply, phone)

            pilot("seed")
            pilot()
            original = target.create

            def lost_ack(values):
                original(values)
                raise ProbeFailure("timeout")

            target.create = lost_ack
            try:
                pilot(apply=True)
                raise AssertionError("Lost acknowledgement must be recorded as failed")
            except ProbeFailure:
                pass
            finally:
                target.create = original
            pilot(apply=True)
            pilot(apply=True)
            pilot("change-source", phone="+12025550123")
            pilot(apply=True)
        print("Importing real journal history into the real Odoo addon...", flush=True)
        with psycopg.connect(host="127.0.0.1", port=port, dbname="odoo20_migration", user="bambus_journal", password=password) as db:
            partners_before = db.execute("SELECT count(*) FROM res_partner").fetchone()[0]
        result = transfer(journal, MirrorClient(settings))
        assert result["state"] == "imported" and result["counts"]["runs"] == 7
        assert transfer(journal, MirrorClient(settings))["state"] == "unchanged"
        with psycopg.connect(host="127.0.0.1", port=port, dbname="odoo20_migration", user="bambus_journal", password=password) as db:
            assert db.execute("SELECT count(*) FROM res_partner").fetchone()[0] == partners_before
            counts = db.execute("SELECT record_count,run_count,reconciled_count,failure_count,mapping_count FROM bambus_migration_source").fetchone()
            assert counts == (1, 7, 1, 1, 1), counts
            actions = dict(db.execute("SELECT name,res_id FROM ir_model_data WHERE module='bambus_migration_control' AND name LIKE 'action_%'").fetchall())
        print("Journal import, unchanged detection, distinct-record counts and no business writes passed.", flush=True)
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"), headless=True,
                                                  args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url + "/web/login?db=odoo20_migration")
            page.locator('input[name="login"]').fill("admin")
            page.locator('input[name="password"]').fill(admin_password)
            page.locator('button[type="submit"]').click()
            page.wait_for_url("**/odoo**", timeout=60000)
            page.goto(url + "/odoo/action-" + str(actions["action_source"]))
            page.locator(".bm_metric").first.wait_for(timeout=60000)
            assert page.locator(".bm_metric").count() == 4
            assert page.locator(".bm_value").first.inner_text().strip() == "1"
            assert page.locator(".bm_value").first.evaluate("el => parseFloat(getComputedStyle(el).fontSize)") >= 28
            assert page.locator(".o_kanban_ghost").first.evaluate("el => parseFloat(getComputedStyle(el).borderTopWidth)") == 0
            assert page.get_by_text("Monitoring only", exact=False).count() > 0
            page.screenshot(path=str(output / "overview.png"), full_page=True)
            for kind, expected in (("run", 7), ("record", 1), ("mapping", 1), ("issue", 1)):
                page.goto(url + "/odoo/action-" + str(actions["action_" + kind]))
                page.locator(".o_list_view .o_data_row").first.wait_for(timeout=30000)
                assert page.locator(".o_list_view .o_data_row").count() == expected, kind
                assert page.get_by_role("button", name="New", exact=True).count() == 0
            page.goto(url + "/odoo/action-" + str(actions["action_record"]))
            page.locator(".o_list_view .o_data_row").first.click()
            page.get_by_role("button", name="Open target contact").wait_for()
            page.screenshot(path=str(output / "record.png"), full_page=True)
            page.get_by_role("button", name="Open target contact").click()
            page.get_by_text("Bambus migration pilot ui-smoke", exact=False).first.wait_for()
            assert not errors, redact(str(errors))
            browser.close()
        print("Real Chromium overview, lists, read-only controls, record drill-down and target navigation passed.", flush=True)
        from history_fixture import HistoryFixture
        from migration_lab.contact_history import Target, execute_contact, contract
        print("Testing contact history worker against native Odoo 20 and PostgreSQL...", flush=True)
        # Grant a distinct execution role only to the disposable test account.
        docker("exec", "--interactive", app, "odoo", "shell", *odoo[1:], "--no-http",
               input="env.ref('base.user_admin').write({'group_ids': [(4, env.ref('bambus_migration_control.group_contact_trial').id)]})\nenv.cr.commit()\n", log="history-bootstrap.log")
        history_target = Target(settings)
        with HistoryFixture() as fixture:
            fixture.is_company = True
            try:
                execute_contact(fixture.source, history_target, journal, 41)
                raise AssertionError("Native company classification disagreement must remain blocked")
            except Exception as exc:
                assert str(exc) == "trial_company_classification_requires_mapping", str(exc)
            preview = execute_contact(fixture.source, history_target, journal, 41, preserve_legacy_classification=True)
            assert (preview["messages"], preview["attachments"], preview["tracking_changes"]) == (1, 1, 1)
            original_call = history_target.call

            def lost_history_ack(method, *args):
                result = original_call(method, *args)
                if method == "bambus_trial_apply":
                    raise ProbeFailure("timeout")
                return result

            history_target.call = lost_history_ack
            try:
                execute_contact(fixture.source, history_target, journal, 41, True, preview["digest"], True)
                raise AssertionError("Lost contact-history acknowledgement must fail the journal attempt")
            except Exception as exc:
                assert str(exc) == "timeout", str(exc)
            finally:
                history_target.call = original_call
            applied = execute_contact(fixture.source, history_target, journal, 41, True, preview["digest"], True)
            assert applied["operation"] == "no_change"
            repeated = execute_contact(fixture.source, history_target, journal, 41, True, preview["digest"], True)
            assert repeated["target_id"] == applied["target_id"] and repeated["operation"] == "no_change"
            fixture.phone = "+12025550123"
            try:
                execute_contact(fixture.source, history_target, journal, 41, True, preview["digest"], True)
                raise AssertionError("Unreviewed source changes must block")
            except Exception as exc:
                assert str(exc) == "source_changed_regenerate_trial_plan", str(exc)
            changed = execute_contact(fixture.source, history_target, journal, 41, preserve_legacy_classification=True)
            updated = execute_contact(fixture.source, history_target, journal, 41, True, changed["digest"], True)
            assert updated["operation"] == "update" and updated["target_id"] == applied["target_id"]
            assert all(op == "search_read" for _, op in fixture.calls)
        evidence = journal.connection.execute("SELECT kind,count(*) AS n FROM bambus_pilot.history_items GROUP BY kind ORDER BY kind").fetchall()
        assert evidence == [{"kind": "attachment", "n": 1}, {"kind": "message", "n": 1}], evidence
        assert transfer(journal, MirrorClient(settings))["state"] == "imported"
        with psycopg.connect(host="127.0.0.1", port=port, dbname="odoo20_migration", user="bambus_journal", password=password) as db:
            assert db.execute("SELECT record_count FROM bambus_migration_source").fetchone()[0] == 2
            assert db.execute("SELECT count(*) FROM mail_message WHERE model='res.partner' AND res_id=%s", (applied["target_id"],)).fetchone()[0] == 1
            assert db.execute("SELECT count(*) FROM ir_attachment WHERE res_model='res.partner' AND res_id=%s", (applied["target_id"],)).fetchone()[0] == 1
            company_type = db.execute("SELECT is_company,bambus_legacy_classification,vat FROM res_partner WHERE id=%s", (applied["target_id"],)).fetchone()
            assert company_type[:2] == (True, "company") and company_type[2] in (None, ""), company_type
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"), headless=True,
                                                  args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url + "/web/login?db=odoo20_migration")
            page.locator('input[name="login"]').fill("admin")
            page.locator('input[name="password"]').fill(admin_password)
            page.locator('button[type="submit"]').click()
            page.wait_for_url("**/odoo**", timeout=60000)
            page.goto(url + "/odoo/action-" + str(actions["action_record"]))
            page.locator(".o_list_view .o_data_row").filter(has=page.get_by_text("41", exact=True)).click(timeout=30000)
            page.get_by_role("button", name="Open target contact").click()
            page.get_by_text("Synthetic historical note", exact=False).first.wait_for(timeout=30000)
            page.get_by_text("original author: Synthetic author", exact=False).first.wait_for()
            page.get_by_text("synthetic.txt", exact=False).first.wait_for()
            page.get_by_text("Imported company", exact=True).first.wait_for()
            page.screenshot(path=str(output / "history-contact.png"), full_page=True)
            (output / "history-contact.html").write_text(page.content())
            page.locator("label:visible").filter(has_text="Imported contact type").first.wait_for()
            assert page.locator('[name="bambus_legacy_classification"]').first.bounding_box()["y"] > page.locator('[name="vat"]').first.bounding_box()["y"]
            page.screenshot(path=str(output / "history-contact.png"), full_page=True)
            assert not errors, redact(str(errors))
            browser.close()
        print("History preview, lost-ack recovery, rerun, source-change guard, update and UI journal transfer passed.", flush=True)
        (output / "result.json").write_text(json.dumps({"odoo_tests": int(summaries[-1][2]), "browser": "passed", "journal_transfer": "passed", "contact_history": "passed", "company_without_tax_id": "passed", "addon_upgrade": "passed", "counts": list(counts)}, indent=2))
        return 0
    finally:
        if journal:
            journal.close()
        log = subprocess.run(base + ["exec", app, "cat", "/var/lib/odoo/http.log"], env=docker_env, capture_output=True, text=True)
        if log.returncode == 0:
            (output / "odoo-http.log").write_text(redact(log.stdout))
        for name in (app, pg):
            subprocess.run(base + ["rm", "--force", name], env=docker_env, capture_output=True)
        subprocess.run(base + ["network", "rm", network], env=docker_env, capture_output=True)
        import shutil
        shutil.rmtree(previous)


if __name__ == "__main__":
    raise SystemExit(main())

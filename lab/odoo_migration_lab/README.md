# Odoo 12 to Odoo 20 Migration Laboratory

Experimental, isolated setup for Ubuntu 24.04 LTS. **Not production-ready.** Source is cloned from official Odoo Community Git branches. Each container has its own Python virtual environment. PostgreSQL 12 and 16 run as independent services.

## Requirements
- Ubuntu 24.04, Docker Engine, Docker Compose plugin, Git
- Recommended 8 GB RAM and 25+ GB free disk
- Docker daemon access (run with suitable permissions)

Install Docker Engine and the Compose plugin using Docker's official Ubuntu instructions: https://docs.docker.com/engine/install/ubuntu/

## Run
```bash
bash install.sh
```

The installer clones both branches, builds both images in parallel, starts PostgreSQL, initializes Odoo 12 with default demo data and Odoo 20 without demo data, then starts both applications.

- Odoo 12: http://localhost:8012 (database: `odoo12_demo`)
- Odoo 20: http://localhost:8020 (database: `odoo20_migration`)

Both are bound to localhost. For a remote server, use SSH port forwarding:
```bash
ssh -L 8012:127.0.0.1:8012 -L 8020:127.0.0.1:8020 user@server
```

## Useful commands
```bash
docker compose ps
docker compose logs -f odoo12
docker compose logs -f odoo20
docker compose stop
docker compose up -d
```

## Important caveats
- The old Odoo 12 Python requirements may fail to build against a newer OS library even in the isolated Python 3.7 image. This script is a **starting laboratory installer, not an installation verified end-to-end**. If build fails, inspect `docker compose build odoo12` output and pin/patch the incompatible package, rather than changing the host Python.
- Initial demo records depend on Odoo's built-in demo fixtures for the installed modules. You can add controlled sample partners/products manually.
- Some Odoo 20 features/modules may need extra system libraries. wkhtmltopdf is not included, as PDF reports are outside this initial data migration experiment.
- Both databases contain an initial Odoo admin user (normally `admin` / `admin`); change passwords immediately if access is extended beyond localhost.
- The example database passwords in compose.yaml are lab-only. Replace them before using non-synthetic data.
- The Odoo 12 image uses end-of-life Python and PostgreSQL versions: **never expose these services to the internet**.
- Odoo 20's API behavior must be tested before building an XML-RPC importer.
- Do not run `docker compose down -v` unless you intentionally want to delete database and filestore volumes.

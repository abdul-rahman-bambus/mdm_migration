#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
: "${LAB_PG12_PASSWORD:?Export the existing pg12 laboratory database password}"
: "${LAB_PG20_PASSWORD:?Export the existing pg20 laboratory database password}"
command -v git >/dev/null || { echo 'Install git first: sudo apt install git'; exit 1; }
command -v docker >/dev/null || { echo 'Install Docker Engine and Compose plugin first.'; exit 1; }
docker compose version >/dev/null || { echo 'Docker Compose plugin not found.'; exit 1; }
mkdir -p source
if [ ! -d source/odoo12/.git ]; then git clone --depth 1 --branch 12.0 https://github.com/odoo/odoo.git source/odoo12; fi
if [ ! -d source/odoo20/.git ]; then git clone --depth 1 --branch 20.0 https://github.com/odoo/odoo.git source/odoo20; fi
# The two independent image builds can run concurrently.
docker compose build --parallel odoo12 odoo20
docker compose up -d pg12 pg20
# Do not reinitialize existing databases.
if ! docker compose exec -T pg12 psql -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='odoo12_demo'" | grep -qx 1; then
  docker compose run --rm --no-deps odoo12 /opt/venv/bin/python /opt/odoo/odoo-bin --db_host=pg12 --db_user=odoo "--db_password=${LAB_PG12_PASSWORD}" -d odoo12_demo -i base,product,contacts --stop-after-init --data-dir=/var/lib/odoo
fi
if ! docker compose exec -T pg20 psql -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='odoo20_migration'" | grep -qx 1; then
  docker compose run --rm --no-deps odoo20 /opt/venv/bin/python /opt/odoo/odoo-bin --db_host=pg20 --db_user=odoo "--db_password=${LAB_PG20_PASSWORD}" -d odoo20_migration -i base,product,contacts --without-demo=all --stop-after-init --data-dir=/var/lib/odoo
fi
docker compose up -d odoo12 odoo20
printf '\nOdoo 12: http://localhost:8012\nOdoo 20: http://localhost:8020\n'

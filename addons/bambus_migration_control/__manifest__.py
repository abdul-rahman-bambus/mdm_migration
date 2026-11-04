{
    "name": "Bambus Migration Control",
    "summary": "Journal-backed migration monitoring and reconciliation history",
    "version": "20.0.2.0.0",
    "license": "LGPL-3",
    "depends": ["base", "web", "mail"],
    "data": ["security/groups.xml", "security/ir.access.csv", "views/monitor_views.xml"],
    "assets": {"web.assets_backend": ["bambus_migration_control/static/src/scss/overview.scss"]},
    "application": True,
    "installable": True,
}

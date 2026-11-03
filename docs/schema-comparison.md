# Observed schema comparison

The committed `odoo-schema-20261103-122514-132435.json` parses successfully and
contains all three core models without error entries.

| Model | Source | Target | Source-only | Target-only |
|---|---:|---:|---:|---:|
| product.template | 75 | 92 | 23 | 40 |
| product.product | 83 | 111 | 25 | 53 |
| res.partner | 87 | 116 | 23 | 52 |

Totals: 245 source field entries, 319 target entries and 390 union entries.
These are field counts, not business record counts or migration success rates.

Run from the repository root using a new output directory:

```sh
python3 -m migration_lab.schema odoo-schema-20261103-122514-132435.json --output-dir reports/schema-review-1
```

The command is offline. It emits comparison.json, comparison.md, fields.csv and
mapping-draft.json. The input SHA-256 is included for provenance. Checked-in
results are under `docs/schema-reports/odoo12-20-initial/`.

The comparator validates snapshot metadata, compares selection keys independently
of ordering/labels, flags changed types/relations/required status, and marks
readonly, related, binary, company-dependent and nonstored fields for review.
Every source field is accounted for. Same-name scalar candidates remain
unapproved. Source-only fields are not automatically renamed; target-only fields
are not silently assigned defaults.

Computed metadata is absent from the supplied snapshot. Defaults and API
writeability remain unknown. See field-mapping.md for concrete review decisions.
Next: collect installed modules and dependent-model metadata with the local
inventory command. No migration writes or reconciliation have occurred.

# Initial mapping review

Evidence: committed Odoo 12/20 core-model snapshot. The generated
`mapping-draft.json` accounts for all 245 source fields and target-only fields.
All approved targets and transformations remain null; all decisions are unresolved.
Version: `odoo12-20.lab.v1-draft`. This is not executable migration configuration.

| Observed difference | Migration impact / next verification |
|---|---|
| Product description and partner comment: text → html | Escape plain text and define normalized reconciliation. |
| image/image_medium/image_small source-only; image_1920 family target-only | Candidate image mapping; resizing/storage behavior needs testing. |
| Variant image_variant source-only | Inspect variant image fields and fallback semantics. |
| Product uom_po_id absent on target | Inspect purchase/UoM modules; do not guess a replacement. |
| Partner customer/supplier absent on target | Inspect modules; target also lacks customer_rank/supplier_rank. |
| Partner company_type absent; is_company target readonly | Determine supported company/person classification behavior. |
| Partner mobile absent on target | Do not overwrite phone or silently drop the mobile number. |
| Partner type selection lacks private | Explicit visibility/business decision required. |
| Product consu label changes to Goods; combo added | Compare keys and semantics separately; do not assume stock/storage behavior. |
| Target service_tracking and base_unit_count are newly required | Inspect defaults and writeability before loading. |
| Variant fields extensively related/nonstored | Resolve template/attribute dependencies and avoid duplicate variants. |
| Partner channel relation mail.channel → discuss.channel | Relational mapping and scope review needed; never reuse source IDs. |

Source-only means absent in this installed schema, not proven version-wide
removal. Every field is listed in the generated report. Computed status,
defaults and API writeability remain unknown where not exported. Module and
dependent-model inventory is required before approving concrete mappings.

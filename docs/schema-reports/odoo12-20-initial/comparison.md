# Observed schema comparison

Input: `odoo-schema-20261103-122514-132435.json`; SHA-256: `38c10099945066679442f4d0d27135ad626f1e58838917d408e807769cf45885`.

Generated offline from user-local metadata. No API writes, mapping approvals or migration occurred.
Computed status and API writeability remain unknown where not supplied. Source-only fields may
reflect installed-module differences; absence does not prove a version-wide removal.

Selection keys are compared independently of labels and ordering. Every field appears below.

## product.product

Source fields: 83; target fields: 111.

| Field | Source type | Target type | Review flags |
|---|---|---|---|
| __last_update | datetime | absent | source_only, system_field_do_not_copy |
| active | boolean | boolean | computed_status_unknown, same_name_scalar_candidate |
| activity_date_deadline | date | date | target_readonly, nonstored_field_review, computed_status_unknown |
| activity_exception_decoration | absent | selection | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| activity_exception_icon | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| activity_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| activity_plans_ids | absent | many2many | target_only, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| activity_state | selection | selection | target_readonly, nonstored_field_review, computed_status_unknown |
| activity_summary | char | char | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| activity_type_icon | absent | char | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| activity_type_id | many2one | many2one | related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| activity_user_id | many2one | many2one | readonly_changed, related_changed, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| additional_product_tag_ids | absent | many2many | target_only, relational_mapping_required, computed_status_unknown |
| all_product_tag_ids | absent | many2many | target_only, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| attribute_line_ids | one2many | one2many | related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| attribute_value_ids | many2many | absent | source_only |
| barcode | char | char | computed_status_unknown, same_name_scalar_candidate |
| base_unit_count | absent | float | target_only, new_required_field, computed_status_unknown |
| base_unit_id | absent | many2one | target_only, relational_mapping_required, computed_status_unknown |
| base_unit_name | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| base_unit_price | absent | monetary | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| can_image_1024_be_zoomed | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| can_image_variant_1024_be_zoomed | absent | boolean | target_only, target_readonly, computed_status_unknown |
| catalog_is_in_order | absent | boolean | target_only, nonstored_field_review, computed_status_unknown |
| categ_id | many2one | many2one | required_changed, related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| code | char | char | target_readonly, nonstored_field_review, computed_status_unknown |
| color | integer | integer | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| combination_indices | absent | char | target_only, target_readonly, computed_status_unknown |
| combo_ids | absent | many2many | target_only, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| company_id | many2one | many2one | related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| cost_currency_id | many2one | many2one | related_changed, target_readonly, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| create_date | datetime | datetime | target_readonly, computed_status_unknown, system_field_do_not_copy |
| create_uid | many2one | many2one | target_readonly, relational_mapping_required, computed_status_unknown, system_field_do_not_copy |
| currency_id | many2one | many2one | related_changed, target_readonly, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| default_code | char | char | computed_status_unknown, same_name_scalar_candidate |
| description | text | html | type_changed, related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| description_purchase | text | text | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| description_sale | text | text | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| display_name | char | char | target_readonly, nonstored_field_review, computed_status_unknown, system_field_do_not_copy |
| extra_uom_ids | absent | many2many | target_only, relational_mapping_required, computed_status_unknown |
| fixed_pricelist_rule_ids | absent | one2many | target_only, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| free_qty | absent | float | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| has_configurable_attributes | absent | boolean | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| has_message | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| id | integer | integer | target_readonly, computed_status_unknown, system_field_do_not_copy |
| image | binary | absent | source_only |
| image_1024 | absent | binary | target_only, target_readonly, nonstored_field_review, binary_validation_required, computed_status_unknown |
| image_128 | absent | binary | target_only, target_readonly, nonstored_field_review, binary_validation_required, computed_status_unknown |
| image_1920 | absent | binary | target_only, nonstored_field_review, binary_validation_required, computed_status_unknown |
| image_256 | absent | binary | target_only, target_readonly, nonstored_field_review, binary_validation_required, computed_status_unknown |
| image_512 | absent | binary | target_only, target_readonly, nonstored_field_review, binary_validation_required, computed_status_unknown |
| image_medium | binary | absent | source_only |
| image_small | binary | absent | source_only |
| image_variant | binary | absent | source_only |
| image_variant_1024 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_variant_128 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_variant_1920 | absent | binary | target_only, binary_validation_required, computed_status_unknown |
| image_variant_256 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_variant_512 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| import_attribute_values | absent | char | target_only, nonstored_field_review, computed_status_unknown |
| incoming_qty | absent | float | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| is_dynamically_created | absent | boolean | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| is_favorite | absent | boolean | target_only, related_field_review, computed_status_unknown |
| is_product_variant | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| is_storable | absent | boolean | target_only, related_field_review, nonstored_field_review, computed_status_unknown |
| item_ids | one2many | absent | source_only |
| list_price | float | float | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| lst_price | float | float | store_changed, computed_status_unknown, same_name_scalar_candidate |
| message_attachment_count | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| message_channel_ids | many2many | absent | source_only |
| message_follower_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| message_has_error | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| message_has_error_counter | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| message_has_sms_error | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| message_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| message_is_follower | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| message_main_attachment_id | many2one | absent | source_only |
| message_needaction | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| message_needaction_counter | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| message_partner_ids | many2many | many2many | readonly_changed, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| message_unread | boolean | absent | source_only |
| message_unread_counter | integer | absent | source_only |
| my_activity_date_deadline | absent | date | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| name | char | char | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| outgoing_qty | absent | float | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| packaging_ids | one2many | absent | source_only |
| partner_ref | char | char | target_readonly, nonstored_field_review, computed_status_unknown |
| price | float | absent | source_only |
| price_extra | float | float | target_readonly, nonstored_field_review, computed_status_unknown |
| pricelist_id | many2one | absent | source_only |
| pricelist_item_ids | many2many | absent | source_only |
| pricelist_rule_ids | absent | one2many | target_only, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| product_document_count | absent | integer | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| product_document_ids | absent | one2many | target_only, relational_mapping_required, computed_status_unknown |
| product_properties | absent | properties | target_only, related_field_review, nonstored_field_review, computed_status_unknown |
| product_tag_ids | absent | many2many | target_only, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| product_template_attribute_value_ids | many2many | many2many | readonly_changed, store_changed, relational_mapping_required, computed_status_unknown |
| product_template_variant_value_ids | absent | many2many | target_only, relational_mapping_required, computed_status_unknown |
| product_tmpl_id | many2one | many2one | relational_mapping_required, computed_status_unknown |
| product_tooltip | absent | char | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| product_uom_ids | absent | one2many | target_only, relational_mapping_required, computed_status_unknown |
| product_variant_count | integer | integer | related_changed, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| product_variant_id | many2one | many2one | related_changed, target_readonly, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| product_variant_ids | one2many | one2many | related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| purchase_ok | boolean | boolean | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| qty_available | absent | float | target_only, company_context_required, computed_status_unknown |
| rental | boolean | absent | source_only |
| sale_ok | boolean | boolean | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| seller_ids | one2many | one2many | related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| sequence | integer | integer | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| service_tracking | absent | selection | target_only, new_required_field, related_field_review, nonstored_field_review, computed_status_unknown |
| show_qty_update_button | absent | boolean | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| show_sales_price_page | absent | boolean | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| standard_price | float | float | store_changed, company_context_required, computed_status_unknown |
| type | selection | selection | related_changed, selection_keys_added, selection_labels_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| uom_id | many2one | many2one | related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| uom_ids | absent | many2many | target_only, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| uom_name | char | char | related_changed, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| uom_po_id | many2one | absent | source_only |
| valid_archived_variant_ids | many2many | absent | source_only |
| valid_existing_variant_ids | many2many | absent | source_only |
| valid_product_attribute_ids | many2many | absent | source_only |
| valid_product_attribute_value_ids | many2many | absent | source_only |
| valid_product_attribute_value_wnva_ids | many2many | absent | source_only |
| valid_product_attribute_wnva_ids | many2many | absent | source_only |
| valid_product_template_attribute_line_ids | many2many | many2many | related_changed, target_readonly, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| valid_product_template_attribute_line_wnva_ids | many2many | absent | source_only |
| variant_seller_ids | one2many | one2many | related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| virtual_available | absent | float | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| volume | float | float | computed_status_unknown, same_name_scalar_candidate |
| volume_uom_name | absent | char | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| weight | float | float | computed_status_unknown, same_name_scalar_candidate |
| weight_uom_id | many2one | absent | source_only |
| weight_uom_name | char | char | related_changed, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| write_date | datetime | datetime | target_readonly, computed_status_unknown, system_field_do_not_copy |
| write_uid | many2one | many2one | target_readonly, relational_mapping_required, computed_status_unknown, system_field_do_not_copy |

## product.template

Source fields: 75; target fields: 92.

| Field | Source type | Target type | Review flags |
|---|---|---|---|
| __last_update | datetime | absent | source_only, system_field_do_not_copy |
| active | boolean | boolean | computed_status_unknown, same_name_scalar_candidate |
| activity_date_deadline | date | date | target_readonly, nonstored_field_review, computed_status_unknown |
| activity_exception_decoration | absent | selection | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| activity_exception_icon | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| activity_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| activity_plans_ids | absent | many2many | target_only, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| activity_state | selection | selection | target_readonly, nonstored_field_review, computed_status_unknown |
| activity_summary | char | char | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| activity_type_icon | absent | char | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| activity_type_id | many2one | many2one | related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| activity_user_id | many2one | many2one | readonly_changed, related_changed, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| attribute_line_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| barcode | char | char | store_changed, related_changed, computed_status_unknown, same_name_scalar_candidate |
| base_unit_count | absent | float | target_only, new_required_field, computed_status_unknown |
| base_unit_id | absent | many2one | target_only, relational_mapping_required, computed_status_unknown |
| base_unit_name | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| base_unit_price | absent | monetary | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| can_image_1024_be_zoomed | absent | boolean | target_only, target_readonly, computed_status_unknown |
| categ_id | many2one | many2one | required_changed, relational_mapping_required, computed_status_unknown |
| color | integer | integer | computed_status_unknown, same_name_scalar_candidate |
| combo_ids | absent | many2many | target_only, relational_mapping_required, computed_status_unknown |
| company_id | many2one | many2one | relational_mapping_required, computed_status_unknown |
| cost_currency_id | many2one | many2one | target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| create_date | datetime | datetime | target_readonly, computed_status_unknown, system_field_do_not_copy |
| create_uid | many2one | many2one | target_readonly, relational_mapping_required, computed_status_unknown, system_field_do_not_copy |
| currency_id | many2one | many2one | target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| default_code | char | char | computed_status_unknown, same_name_scalar_candidate |
| description | text | html | type_changed, computed_status_unknown |
| description_purchase | text | text | computed_status_unknown, same_name_scalar_candidate |
| description_sale | text | text | computed_status_unknown, same_name_scalar_candidate |
| display_name | char | char | target_readonly, nonstored_field_review, computed_status_unknown, system_field_do_not_copy |
| fixed_pricelist_rule_ids | absent | one2many | target_only, relational_mapping_required, computed_status_unknown |
| free_qty | absent | float | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| has_configurable_attributes | absent | boolean | target_only, target_readonly, computed_status_unknown |
| has_message | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| id | integer | integer | target_readonly, computed_status_unknown, system_field_do_not_copy |
| image | binary | absent | source_only |
| image_1024 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_128 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_1920 | absent | binary | target_only, binary_validation_required, computed_status_unknown |
| image_256 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_512 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_medium | binary | absent | source_only |
| image_small | binary | absent | source_only |
| import_attribute_values | absent | char | target_only, nonstored_field_review, computed_status_unknown |
| incoming_qty | absent | float | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| is_dynamically_created | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| is_favorite | absent | boolean | target_only, computed_status_unknown |
| is_product_variant | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| is_storable | absent | boolean | target_only, computed_status_unknown |
| item_ids | one2many | absent | source_only |
| list_price | float | float | computed_status_unknown, same_name_scalar_candidate |
| lst_price | float | absent | source_only |
| message_attachment_count | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| message_channel_ids | many2many | absent | source_only |
| message_follower_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| message_has_error | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| message_has_error_counter | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| message_has_sms_error | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| message_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| message_is_follower | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| message_main_attachment_id | many2one | absent | source_only |
| message_needaction | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| message_needaction_counter | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| message_partner_ids | many2many | many2many | readonly_changed, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| message_unread | boolean | absent | source_only |
| message_unread_counter | integer | absent | source_only |
| my_activity_date_deadline | absent | date | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| name | char | char | computed_status_unknown, same_name_scalar_candidate |
| outgoing_qty | absent | float | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| packaging_ids | one2many | absent | source_only |
| price | float | absent | source_only |
| pricelist_id | many2one | absent | source_only |
| pricelist_rule_ids | absent | one2many | target_only, relational_mapping_required, computed_status_unknown |
| product_document_count | absent | integer | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| product_document_ids | absent | one2many | target_only, relational_mapping_required, computed_status_unknown |
| product_properties | absent | properties | target_only, computed_status_unknown |
| product_tag_ids | absent | many2many | target_only, relational_mapping_required, computed_status_unknown |
| product_tooltip | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| product_variant_count | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| product_variant_id | many2one | many2one | target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| product_variant_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| purchase_ok | boolean | boolean | computed_status_unknown, same_name_scalar_candidate |
| qty_available | absent | float | target_only, nonstored_field_review, computed_status_unknown |
| rental | boolean | absent | source_only |
| sale_ok | boolean | boolean | computed_status_unknown, same_name_scalar_candidate |
| seller_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| sequence | integer | integer | computed_status_unknown, same_name_scalar_candidate |
| service_tracking | absent | selection | target_only, new_required_field, computed_status_unknown |
| show_qty_update_button | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| show_sales_price_page | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| standard_price | float | float | nonstored_field_review, computed_status_unknown |
| type | selection | selection | selection_keys_added, selection_labels_changed, computed_status_unknown |
| uom_id | many2one | many2one | relational_mapping_required, computed_status_unknown |
| uom_ids | absent | many2many | target_only, relational_mapping_required, computed_status_unknown |
| uom_name | char | char | related_changed, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| uom_po_id | many2one | absent | source_only |
| valid_archived_variant_ids | many2many | absent | source_only |
| valid_existing_variant_ids | many2many | absent | source_only |
| valid_product_attribute_ids | many2many | absent | source_only |
| valid_product_attribute_value_ids | many2many | absent | source_only |
| valid_product_attribute_value_wnva_ids | many2many | absent | source_only |
| valid_product_attribute_wnva_ids | many2many | absent | source_only |
| valid_product_template_attribute_line_ids | many2many | many2many | target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| valid_product_template_attribute_line_wnva_ids | many2many | absent | source_only |
| variant_seller_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| virtual_available | absent | float | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| volume | float | float | computed_status_unknown, same_name_scalar_candidate |
| volume_uom_name | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| weight | float | float | computed_status_unknown, same_name_scalar_candidate |
| weight_uom_id | many2one | absent | source_only |
| weight_uom_name | char | char | related_changed, target_readonly, nonstored_field_review, computed_status_unknown |
| write_date | datetime | datetime | target_readonly, computed_status_unknown, system_field_do_not_copy |
| write_uid | many2one | many2one | target_readonly, relational_mapping_required, computed_status_unknown, system_field_do_not_copy |

## res.partner

Source fields: 87; target fields: 116.

| Field | Source type | Target type | Review flags |
|---|---|---|---|
| __last_update | datetime | absent | source_only, system_field_do_not_copy |
| active | boolean | boolean | computed_status_unknown, same_name_scalar_candidate |
| active_lang_count | absent | integer | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| activity_date_deadline | date | date | target_readonly, nonstored_field_review, computed_status_unknown |
| activity_exception_decoration | absent | selection | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| activity_exception_icon | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| activity_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| activity_plans_ids | absent | many2many | target_only, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| activity_state | selection | selection | target_readonly, nonstored_field_review, computed_status_unknown |
| activity_summary | char | char | related_changed, related_field_review, nonstored_field_review, computed_status_unknown |
| activity_type_icon | absent | char | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| activity_type_id | many2one | many2one | related_changed, relational_mapping_required, related_field_review, nonstored_field_review, computed_status_unknown |
| activity_user_id | many2one | many2one | readonly_changed, related_changed, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| additional_identifiers | absent | json | target_only, computed_status_unknown |
| additional_info | char | absent | source_only |
| address | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| address_inline | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| application_statistics | absent | json | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| available_additional_identifiers_metadata | absent | json | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| avatar_1024 | absent | binary | target_only, target_readonly, nonstored_field_review, binary_validation_required, computed_status_unknown |
| avatar_128 | absent | binary | target_only, target_readonly, nonstored_field_review, binary_validation_required, computed_status_unknown |
| avatar_1920 | absent | binary | target_only, target_readonly, nonstored_field_review, binary_validation_required, computed_status_unknown |
| avatar_256 | absent | binary | target_only, target_readonly, nonstored_field_review, binary_validation_required, computed_status_unknown |
| avatar_512 | absent | binary | target_only, target_readonly, nonstored_field_review, binary_validation_required, computed_status_unknown |
| bank_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| barcode | char | char | company_dependent_changed, company_context_required, computed_status_unknown |
| category_id | many2many | many2many | relational_mapping_required, computed_status_unknown |
| channel_ids | many2many | many2many | relation_changed, relational_mapping_required, computed_status_unknown |
| channel_member_ids | absent | one2many | target_only, relational_mapping_required, computed_status_unknown |
| child_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| city | char | char | computed_status_unknown, same_name_scalar_candidate |
| city_id | absent | many2one | target_only, relational_mapping_required, computed_status_unknown |
| color | integer | integer | computed_status_unknown, same_name_scalar_candidate |
| comment | text | html | type_changed, computed_status_unknown |
| commercial_company_name | char | char | related_changed, target_readonly, related_field_review, computed_status_unknown |
| commercial_partner_id | many2one | many2one | target_readonly, relational_mapping_required, computed_status_unknown |
| company_id | many2one | many2one | relational_mapping_required, computed_status_unknown |
| company_name | char | absent | source_only |
| company_type | selection | absent | source_only |
| complete_name | absent | char | target_only, target_readonly, computed_status_unknown |
| contact_address | char | char | target_readonly, nonstored_field_review, computed_status_unknown |
| contact_address_inline | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| country_code | absent | char | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| country_enforce_cities | absent | boolean | target_only, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| country_id | many2one | many2one | relational_mapping_required, computed_status_unknown |
| create_date | datetime | datetime | target_readonly, computed_status_unknown, system_field_do_not_copy |
| create_uid | many2one | many2one | target_readonly, relational_mapping_required, computed_status_unknown, system_field_do_not_copy |
| credit_limit | float | absent | source_only |
| customer | boolean | absent | source_only |
| date | date | absent | source_only |
| display_name | char | char | store_changed, target_readonly, nonstored_field_review, computed_status_unknown, system_field_do_not_copy |
| email | char | char | computed_status_unknown, same_name_scalar_candidate |
| email_formatted | char | char | target_readonly, nonstored_field_review, computed_status_unknown |
| email_normalized | absent | char | target_only, target_readonly, computed_status_unknown |
| employee | boolean | boolean | computed_status_unknown, same_name_scalar_candidate |
| function | char | char | computed_status_unknown, same_name_scalar_candidate |
| has_message | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| has_vat | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| id | integer | integer | target_readonly, computed_status_unknown, system_field_do_not_copy |
| im_status | char | absent | source_only |
| image | binary | absent | source_only |
| image_1024 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_128 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_1920 | absent | binary | target_only, binary_validation_required, computed_status_unknown |
| image_256 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_512 | absent | binary | target_only, target_readonly, related_field_review, binary_validation_required, computed_status_unknown |
| image_medium | binary | absent | source_only |
| image_small | binary | absent | source_only |
| industry_id | many2one | many2one | relational_mapping_required, computed_status_unknown |
| is_blacklisted | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| is_company | boolean | boolean | readonly_changed, target_readonly, computed_status_unknown |
| is_in_call | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| is_pricelist_manually_set | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| is_public | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| lang | selection | selection | selection_labels_changed, computed_status_unknown, same_name_scalar_candidate |
| main_user_id | absent | many2one | target_only, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| message_attachment_count | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| message_bounce | integer | integer | computed_status_unknown, same_name_scalar_candidate |
| message_channel_ids | many2many | absent | source_only |
| message_follower_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| message_has_error | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| message_has_error_counter | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| message_has_sms_error | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| message_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| message_is_follower | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| message_main_attachment_id | many2one | absent | source_only |
| message_needaction | boolean | boolean | target_readonly, nonstored_field_review, computed_status_unknown |
| message_needaction_counter | integer | integer | target_readonly, nonstored_field_review, computed_status_unknown |
| message_partner_ids | many2many | many2many | readonly_changed, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| message_unread | boolean | absent | source_only |
| message_unread_counter | integer | absent | source_only |
| mobile | char | absent | source_only |
| my_activity_date_deadline | absent | date | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| name | char | char | computed_status_unknown, same_name_scalar_candidate |
| parent_id | many2one | many2one | relational_mapping_required, computed_status_unknown |
| parent_name | char | char | related_changed, target_readonly, related_field_review, nonstored_field_review, computed_status_unknown |
| partner_gid | integer | absent | source_only |
| partner_latitude | absent | float | target_only, computed_status_unknown |
| partner_longitude | absent | float | target_only, computed_status_unknown |
| partner_share | boolean | boolean | target_readonly, computed_status_unknown |
| phone | char | char | computed_status_unknown, same_name_scalar_candidate |
| phone_blacklisted | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| phone_formatted | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| phone_mobile_search | absent | char | target_only, nonstored_field_review, computed_status_unknown |
| phone_sanitized | absent | char | target_only, target_readonly, computed_status_unknown |
| phone_sanitized_blacklisted | absent | boolean | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| properties | absent | properties | target_only, computed_status_unknown |
| properties_base_definition_id | absent | many2one | target_only, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| property_product_pricelist | many2one | many2one | relational_mapping_required, nonstored_field_review, computed_status_unknown |
| ref | char | char | computed_status_unknown, same_name_scalar_candidate |
| rtc_session_ids | absent | one2many | target_only, relational_mapping_required, computed_status_unknown |
| same_vat_partner_id | absent | many2one | target_only, target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| self | many2one | many2one | target_readonly, relational_mapping_required, nonstored_field_review, computed_status_unknown |
| signup_expiration | datetime | absent | source_only |
| signup_token | char | absent | source_only |
| signup_type | char | char | computed_status_unknown, same_name_scalar_candidate |
| signup_url | char | absent | source_only |
| signup_valid | boolean | absent | source_only |
| specific_property_product_pricelist | absent | many2one | target_only, relational_mapping_required, company_context_required, computed_status_unknown |
| state_id | many2one | many2one | relational_mapping_required, computed_status_unknown |
| street | char | char | computed_status_unknown, same_name_scalar_candidate |
| street2 | char | char | computed_status_unknown, same_name_scalar_candidate |
| street_name | absent | char | target_only, computed_status_unknown |
| street_number | absent | char | target_only, computed_status_unknown |
| street_number2 | absent | char | target_only, computed_status_unknown |
| supplier | boolean | absent | source_only |
| title | many2one | absent | source_only |
| type | selection | selection | selection_keys_removed, selection_labels_changed, computed_status_unknown |
| type_address_label | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| tz | selection | selection | selection_keys_removed, selection_keys_added, computed_status_unknown |
| tz_offset | char | char | target_readonly, nonstored_field_review, computed_status_unknown |
| user_id | many2one | many2one | relational_mapping_required, computed_status_unknown |
| user_ids | one2many | one2many | relational_mapping_required, computed_status_unknown |
| vat | char | char | computed_status_unknown, same_name_scalar_candidate |
| vat_label | absent | char | target_only, target_readonly, nonstored_field_review, computed_status_unknown |
| website | char | char | computed_status_unknown, same_name_scalar_candidate |
| write_date | datetime | datetime | target_readonly, computed_status_unknown, system_field_do_not_copy |
| write_uid | many2one | many2one | target_readonly, relational_mapping_required, computed_status_unknown, system_field_do_not_copy |
| zip | char | char | computed_status_unknown, same_name_scalar_candidate |

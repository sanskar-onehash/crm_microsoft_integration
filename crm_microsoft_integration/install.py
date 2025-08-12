import frappe
from crm_microsoft_integration.config import custom_fields


def after_install():
    add_event_custom_fields()

    frappe.db.commit()


def add_event_custom_fields():
    for custom_field in custom_fields.EVENT_CUSTOM_FIELDS:
        if not frappe.db.exists(
            "Custom Field", {"fieldname": custom_field["fieldname"]}
        ):
            frappe.get_doc(custom_field).save()

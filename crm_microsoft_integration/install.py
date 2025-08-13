import frappe
from crm_microsoft_integration.config import custom_fields


def after_install():
    add_custom_fields()

    frappe.db.commit()


def add_custom_fields():
    event_custom_fields = []

    # Event Fields
    event_custom_fields.extend(custom_fields.EVENT_CUSTOM_FIELDS)

    # Event Participant Fields
    event_custom_fields.extend(custom_fields.EVENT_PARTICIPANTS_CUSTOM_FIELDS)

    for custom_field in event_custom_fields:
        if not frappe.db.exists(
            "Custom Field",
            {"dt": custom_field["dt"], "fieldname": custom_field["fieldname"]},
        ):
            frappe.get_doc(custom_field).save()

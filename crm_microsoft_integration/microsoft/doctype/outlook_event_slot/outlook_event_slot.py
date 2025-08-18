# Copyright (c) 2025, OneHash and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OutlookEventSlot(Document):
    pass


@frappe.whitelist()
def create_slot(doc):
    if isinstance(doc, str):
        doc = frappe.parse_json(doc)
    frappe.get_doc({"doctype": "Outlook Event Slot", **doc}).save()
    return "success"

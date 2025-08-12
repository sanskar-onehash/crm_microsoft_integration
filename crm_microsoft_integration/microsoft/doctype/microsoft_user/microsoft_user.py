# Copyright (c) 2025, OneHash and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from crm_microsoft_integration.microsoft.integration.user import user

SYNC_MS_USER_TIMEOUT = 25 * 60
SYNC_MS_USER_JOB_NAME = "sync_microsoft_users"
SYNC_MS_USER_PRGRESS_ID = "sync_microsoft_users_progress"


class MicrosoftUser(Document):
    pass


@frappe.whitelist()
def sync_ms_users():
    frappe.enqueue(
        _sync_ms_users,
        queue="default",
        timeout=SYNC_MS_USER_TIMEOUT,
        job_name=SYNC_MS_USER_JOB_NAME,
    )
    return {
        "status": "success",
        "msg": "Microsoft Users syncing started in background.",
        "track_on": SYNC_MS_USER_PRGRESS_ID,
    }


def _sync_ms_users():
    ms_users = user.get_users()
    total = len(ms_users)

    for idx, ms_user in enumerate(ms_users):
        frappe.publish_realtime(
            SYNC_MS_USER_PRGRESS_ID,
            {"progress": idx + 1, "total": total, "title": "Syncing Microsoft Users"},
        )
        existing_user = frappe.db.exists("Microsoft User", {"id": ms_user.get("id")})

        if existing_user:
            user_doc = frappe.get_doc("Microsoft User", existing_user)
            has_updated = False
            for fieldname, new_value in ms_user.items():
                old_value = user_doc.get(fieldname)

                if old_value != new_value:
                    user_doc.set(fieldname, new_value)
                    has_updated = True

            if has_updated:
                user_doc.save()
        else:
            # TODO: Find and link existing system user
            frappe.get_doc({"doctype": "Microsoft User", **ms_user}).save()
    frappe.db.commit()

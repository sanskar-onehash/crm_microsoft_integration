# Copyright (c) 2025, OneHash and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from crm_microsoft_integration.microsoft.integration.group import group

SYNC_MS_GROUP_TIMEOUT = 25 * 60
SYNC_MS_GROUP_JOB_NAME = "sync_microsoft_groups"
SYNC_MS_GROUP_PROGRESS_ID = "sync_microsoft_groups_progress"


class MicrosoftGroup(Document):
    pass


@frappe.whitelist()
def sync_ms_groups():
    frappe.enqueue(
        _sync_ms_groups(),
        queue="default",
        timeout=SYNC_MS_GROUP_TIMEOUT,
        job_name=SYNC_MS_GROUP_JOB_NAME,
    )
    return {
        "status": "success",
        "msg": "Microsoft Groups syncing started in background.",
        "track_on": SYNC_MS_GROUP_PROGRESS_ID,
    }


def _sync_ms_groups():
    ms_groups = group.get_groups(with_users=True)
    total = len(ms_groups)

    for idx, ms_group in enumerate(ms_groups):
        frappe.publish_realtime(
            SYNC_MS_GROUP_PROGRESS_ID,
            {"progress": idx + 1, "total": total, "title": "Syncing Microsoft Groups"},
        )
        existing_group = frappe.db.exists("Microsoft Group", {"id": ms_group["id"]})

        if existing_group:
            group_doc = frappe.get_doc("Microsoft Group", existing_group)
            has_updated = False
            for fieldname, new_value in ms_group.items():
                old_value = group_doc.get(fieldname)

                if fieldname == "users":
                    old_users = {u.microsoft_user for u in old_value}

                    for new_user in new_value:
                        if new_user["microsoft_user"] in old_users:
                            old_users.remove(new_user["microsoft_user"])
                        else:
                            group_doc.append(fieldname, new_user)
                            has_updated = True

                    for user in old_value:
                        if user.microsoft_user in old_users:
                            group_doc.remove(user)
                            has_updated = True

                elif old_value != new_value:
                    group_doc.set(fieldname, new_value)
                    has_updated = True

            if has_updated:
                group_doc.save()
        else:
            frappe.get_doc({"doctype": "Microsoft Group", **ms_group}).save()
    frappe.db.commit()

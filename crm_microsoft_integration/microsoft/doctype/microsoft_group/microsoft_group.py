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
def get_group_users(group_name):
    users = frappe.db.get_all(
        "Microsoft Groups",
        ["parent"],
        {
            "microsoft_group": group_name,
            "parenttype": "Microsoft User",
            "parentfield": "groups",
        },
    )
    return [user.parent for user in users]


@frappe.whitelist()
def sync_ms_groups():
    frappe.enqueue(
        _sync_ms_groups,
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
    total_groups = len(ms_groups)

    member_users = []
    user_wise_groups = {}

    # Update Groups
    for idx, ms_group in enumerate(ms_groups):
        frappe.publish_realtime(
            SYNC_MS_GROUP_PROGRESS_ID,
            {
                "progress": idx + 1,
                "total": total_groups,
                "title": "Syncing Microsoft Groups",
            },
        )

        users = ms_group.pop("users")
        for user in users:
            if user["id"] in user_wise_groups:
                user_wise_groups[user["id"]].append(ms_group["id"])
            else:
                user_wise_groups[user["id"]] = [ms_group["id"]]
                member_users.append(user["id"])

        existing_group = frappe.db.exists("Microsoft Group", {"id": ms_group["id"]})
        if existing_group:
            group_doc = frappe.get_doc("Microsoft Group", existing_group)
            has_group_updated = False
            for fieldname, new_value in ms_group.items():
                old_value = group_doc.get(fieldname)

                if old_value != new_value:
                    group_doc.set(fieldname, new_value)
                    has_group_updated = True

            if has_group_updated:
                group_doc.save()
        else:
            frappe.get_doc({"doctype": "Microsoft Group", **ms_group}).save()

    # Update Group users
    for user in member_users:
        user_doc = frappe.get_doc("Microsoft User", user)
        old_groups = user_doc.get("groups")
        has_user_updated = False

        old_group_names = {user_group.microsoft_group for user_group in old_groups}

        for new_user_group in user_wise_groups[user]:
            if new_user_group not in old_group_names:
                user_doc.append("groups", {"microsoft_group": new_user_group})
                has_user_updated = True
            else:
                old_group_names.remove(new_user_group)

        for old_group in old_groups:
            if old_group.microsoft_group in old_group_names:
                user_doc.remove(old_group)
                has_user_updated = True

        if has_user_updated:
            user_doc.save()

    ## Remove users that are removed from all the groups
    old_group_members = frappe.db.get_all(
        "Microsoft Groups",
        ["name"],
        {
            "parent": ["not in", member_users],
            "parenttype": "Microsoft User",
            "parentfield": "groups",
        },
    )
    for old_member in old_group_members:
        frappe.get_doc("Microsoft Groups", old_member).delete()

    frappe.db.commit()

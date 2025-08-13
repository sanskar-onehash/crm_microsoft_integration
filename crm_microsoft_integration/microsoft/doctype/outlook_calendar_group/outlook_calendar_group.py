# Copyright (c) 2025, OneHash and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from crm_microsoft_integration.microsoft.integration.calendar import calendar

SYNC_MS_CALENDAR_GROUP_TIMEOUT = 25 * 60
SYNC_MS_CALENDAR_GROUP_JOB_NAME = "sync_outlook_calendars"
SYNC_MS_CALENDAR_GROUP_PROGRESS_ID = "sync_outlook_calendars_progress"


class OutlookCalendarGroup(Document):
    pass


@frappe.whitelist()
def sync_outlook_calendar_groups():
    frappe.enqueue(
        _sync_outlook_calendar_groups,
        queue="default",
        timeout=SYNC_MS_CALENDAR_GROUP_TIMEOUT,
        job_name=SYNC_MS_CALENDAR_GROUP_JOB_NAME,
    )
    return {
        "status": "success",
        "msg": "Outlook Calendars syncing started in background.",
        "track_on": SYNC_MS_CALENDAR_GROUP_PROGRESS_ID,
    }


def _sync_outlook_calendar_groups():
    ms_users = frappe.db.get_list("Microsoft User", ["name"])
    user_ids = [ms_user.name for ms_user in ms_users]

    user_cal_groups = calendar.get_users_calendar_groups(user_ids, with_calendar=True)
    total_cal_group_users = len(user_cal_groups)

    for idx, user in enumerate(user_cal_groups):
        frappe.publish_realtime(
            SYNC_MS_CALENDAR_GROUP_PROGRESS_ID,
            {
                "progress": idx + 1,
                "total": total_cal_group_users,
                "title": "Syncing Outlook Calendar Groups",
            },
        )

        for user_cal_group in user_cal_groups[user]:
            group_calendars = user_cal_group.pop("calendars")
            cal_group_name = frappe.db.exists(
                "Outlook Calendar Group", {"id": user_cal_group["id"]}
            )

            if cal_group_name:
                cal_group_doc = frappe.get_doc("Outlook Calendar Group", cal_group_name)
                has_updated = False

                for fieldname, new_value in user.items():
                    old_value = cal_group_doc.get(fieldname)

                    if old_value != new_value:
                        cal_group_doc.set(fieldname, new_value)
                        has_updated = True

                if has_updated:
                    cal_group_doc.save()
            else:
                cal_group = frappe.get_doc(
                    {
                        "doctype": "Outlook Calendar Group",
                        **user_cal_group,
                    }
                ).save()
                cal_group_name = cal_group.get("name")

            for group_calendar in group_calendars:
                existing_calendar = frappe.db.exists(
                    "Outlook Calendar",
                    {"id": group_calendar["id"], "calendar_group": cal_group_name},
                )
                if not existing_calendar:
                    frappe.db.set_value(
                        "Outlook Calendar",
                        {"id": group_calendar["id"]},
                        "calendar_group",
                        cal_group_name,
                    )

    frappe.db.commit()

# Copyright (c) 2025, OneHash and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from crm_microsoft_integration.microsoft.integration.calendar import calendar

SYNC_MS_CALENDAR_TIMEOUT = 25 * 60
SYNC_MS_CALENDAR_JOB_NAME = "sync_outlook_calendars"
SYNC_MS_CALENDAR_PROGRESS_ID = "sync_outlook_calendars_progress"


class OutlookCalendar(Document):

    def before_validate(self):
        self.set_missing_values()

    def set_missing_values(self):
        if not self.get("microsoft_user"):
            pass

    def find_set_microsoft_user(self):
        owner_email = self.get("owner_email")
        if owner_email:
            microsoft_user = frappe.db.get_list(
                "Microsoft User",
                ["name"],
                or_filters={"principal_name": owner_email, "mail": owner_email},
                limit=1,
            )
            if microsoft_user:
                self.set("microsoft_user", microsoft_user[0]["name"])


@frappe.whitelist()
def sync_outlook_calendars():
    frappe.enqueue(
        _sync_outlook_calendars,
        queue="default",
        timeout=SYNC_MS_CALENDAR_TIMEOUT,
        job_name=SYNC_MS_CALENDAR_JOB_NAME,
    )
    return {
        "status": "success",
        "msg": "Outlook Calendars syncing started in background.",
        "track_on": SYNC_MS_CALENDAR_PROGRESS_ID,
    }


def _sync_outlook_calendars():
    ms_users = frappe.db.get_list("Microsoft User", ["name"])
    user_ids = [ms_user.name for ms_user in ms_users]

    user_calendars = calendar.get_users_calendars(user_ids)
    total_calendar_users = len(user_calendars)

    for idx, user in enumerate(user_calendars):
        frappe.publish_realtime(
            SYNC_MS_CALENDAR_PROGRESS_ID,
            {
                "progress": idx + 1,
                "total": total_calendar_users,
                "title": "Syncing Outlook Calendars",
            },
        )

        for ol_calendar in user_calendars[user]:
            existing_calendar = frappe.db.exists(
                "Outlook Calendar", {"id": ol_calendar["id"]}
            )

            if existing_calendar:
                calendar_doc = frappe.get_doc("Outlook Calendar", existing_calendar)
                has_updated = False

                for fieldname, new_value in ol_calendar.items():
                    old_value = calendar_doc.get(fieldname)

                    if old_value != new_value:
                        calendar_doc.set(fieldname, new_value)
                        has_updated = True

                if has_updated:
                    calendar_doc.save()
            else:
                frappe.get_doc(
                    {
                        "doctype": "Outlook Calendar",
                        "enable": 1,
                        "pull_from_outlook_calendar": 1,
                        "push_to_outlook_calendar": 1,
                        "microsoft_user": user,
                        **ol_calendar,
                    }
                ).save()
    frappe.db.commit()

# Copyright (c) 2025, OneHash and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator

WEEK_FIELDS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


class OutlookEventSlot(WebsiteGenerator):
    website = frappe._dict(
        template="templates/generators/event_slot.html",
        condition_field="published",
        page_title_field="subject",
    )

    def get_context(self, context):

        context.update(
            {
                "subject": self.subject,
                "description": self.description,
                "status": self.status or "Unconfirmed",
                "color": self.color,
                "event_location": self.event_location,
                "online_meet": self.add_teams_meet,
                "all_day": self.all_day,
                "slots": [
                    {"start": slot.starts_on, "end": slot.ends_on, "id": slot.name}
                    for slot in self.slot_proposals
                ],
                "repeat_event": self.repeat_this_event,
                "repeat_on": self.repeat_on,
                "repeat_till": self.repeat_till,
                "week_days": [
                    week_field if self.get(week_field) else None
                    for week_field in WEEK_FIELDS
                ],
            }
        )

    def after_insert(self):
        self.db_set(
            {"route": f"slots/{self.name}", "published": 1},
            update_modified=False,
            notify=True,
            commit=True,
        )

    def confirm(self, slot_id, online=True, ignore_permissions=False):
        starts_on = None
        ends_on = None

        for slot in self.slot_proposals:
            if slot.name == slot_id:
                starts_on = slot.starts_on
                ends_on = slot.ends_on
                break

        if not starts_on:
            frappe.throw("Slot not found.")

        event_doc = frappe.get_doc(
            {
                "doctype": "Event",
                "starts_on": starts_on,
                "ends_on": ends_on,
                "custom_outlook_from_slot": self.name,
                "subject": self.subject,
                "description": self.description,
                "color": self.color,
                "repeat_this_event": self.repeat_this_event,
                "all_day": self.all_day,
                "custom_sync_with_ms_calendar": True,
                "custom_add_teams_meet": self.add_teams_meet and online,
                "custom_outlook_location": self.event_location,
                "custom_outlook_calendar": self.outlook_calendar,
                "custom_outlook_organiser": self.organiser,
                "repeat_on": self.repeat_on,
                "repeat_till": self.repeat_till,
            }
        )

        for week_field in WEEK_FIELDS:
            if self.get("week_field"):
                event_doc.set(week_field, True)

        for event_participant in self.event_participants:
            event_doc.append(
                "event_participants",
                {
                    "reference_doctype": event_participant.reference_doctype,
                    "reference_docname": event_participant.reference_docname,
                    "email": event_participant.email,
                    "custom_participant_name": event_participant.custom_participant_name,
                    "custom_required": event_participant.custom_required,
                },
            )

        for user in self.users:
            ms_user_doc = frappe.get_doc("Microsoft User", user.microsoft_user)
            event_doc.append(
                "event_participants",
                {
                    "reference_doctype": ms_user_doc.doctype,
                    "reference_docname": ms_user_doc.name,
                    "email": ms_user_doc.mail
                    or ms_user_doc.user
                    or ms_user_doc.principal_name,
                    "custom_participant_name": ms_user_doc.display_name,
                },
            )

        event_doc.save(ignore_permissions=ignore_permissions)
        self.set("status", "Confirmed")
        self.save()


@frappe.whitelist()
def create_slot(doc):
    if isinstance(doc, str):
        doc = frappe.parse_json(doc)
    frappe.get_doc({"doctype": "Outlook Event Slot", **doc}).save()
    return "success"


@frappe.whitelist(allow_guest=True)
def confirm_slot(slot_id, mode_online=True):
    slot_name = frappe.db.get_value("Outlook Slot Proposals", slot_id, "parent")
    slot_doc = frappe.get_doc("Outlook Event Slot", slot_name)
    slot_doc.confirm(slot_id, mode_online, True)

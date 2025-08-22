# Copyright (c) 2025, OneHash and contributors
# For license information, please see license.txt

import frappe
from frappe import utils
from frappe.model.document import DocStatus
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
                "week_days": [
                    week_field for week_field in WEEK_FIELDS if self.get(week_field)
                ],
            }
        )

        if self.status != "Confirmed":
            context.update(
                {
                    "slots": [
                        {"start": slot.starts_on, "end": slot.ends_on, "id": slot.name}
                        for slot in self.slot_proposals
                    ],
                }
            )

    def validate(self):
        self.validate_repeat()
        return super().validate()

    def validate_repeat(self):
        if self.repeat_this_event and not self.repeat_on:
            frappe.throw("Repeat on is mandatory if chose to repeat this event.")

        if self.repeat_on and self.repeat_on == "Weekly":
            chosen_week_day = None
            for week_field in WEEK_FIELDS:
                if self.get(week_field):
                    chosen_week_day = True
                    break
            if not chosen_week_day:
                frappe.throw("Choose one or more week day/s to repeat on")

    def after_insert(self):
        self.db_set(
            {"route": f"slots/{self.name}", "published": 1},
            update_modified=False,
            notify=True,
            commit=True,
        )

    def confirm(self, slot_id, online=True, ignore_permissions=False):
        if self.selected_slot_start:
            frappe.throw("Event is already scheduled.")

        if online and not self.add_teams_meet:
            frappe.throw("Can not select online mode.")

        starts_on = None
        ends_on = None

        for slot in self.slot_proposals:
            if slot.name == slot_id:
                starts_on = slot.starts_on
                ends_on = slot.ends_on
                break

        if not starts_on:
            frappe.throw("Slot not found.")

        existing_event_name = frappe.db.exists(
            "Event", {"custom_outlook_from_slot": self.name}
        )
        event_doc = None

        if existing_event_name:
            event_doc = frappe.get_doc("Event", existing_event_name)
            event_doc.set("status", "Open")
        else:
            event_doc = frappe.get_doc(
                {
                    "doctype": "Event",
                    "custom_outlook_calendar": self.outlook_calendar,
                    "custom_outlook_organiser": self.organiser,
                    "custom_outlook_from_slot": self.name,
                }
            )
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
            user_doc = frappe.get_doc("User", user.user)
            event_doc.append(
                "event_participants",
                {
                    "reference_doctype": user_doc.doctype,
                    "reference_docname": user_doc.name,
                    "email": user_doc.email,
                    "custom_participant_name": user_doc.full_name,
                },
            )

        event_doc.update(
            {
                "starts_on": starts_on,
                "ends_on": ends_on,
                "subject": self.subject,
                "description": self.description,
                "color": self.color,
                "repeat_this_event": self.repeat_this_event,
                "all_day": self.all_day,
                "custom_sync_with_ms_calendar": True,
                "repeat_on": self.repeat_on,
                "repeat_till": self.repeat_till,
                "event_type": "Public",
            }
        )
        if online:
            event_doc.set("custom_add_teams_meet", True)
        elif self.event_location:
            event_doc.set("custom_outlook_location", self.event_location)

        for week_field in WEEK_FIELDS:
            if self.get("week_field"):
                event_doc.set(week_field, True)
            else:
                event_doc.set(week_field, False)

        event_doc.save(ignore_permissions=ignore_permissions)
        self.update(
            {
                "status": "Confirmed",
                "selected_online": online,
                "selected_slot_start": starts_on,
                "selected_slot_end": ends_on,
                "docstatus": DocStatus.submitted(),
            }
        )
        self.save(ignore_permissions=True)


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


@frappe.whitelist()
def reschedule_event_slots(event_type, event_name, new_slots):
    if event_type not in ["Event", "Outlook Event Slot"]:
        frappe.throw("Invalid event_type")

    if isinstance(new_slots, str):
        new_slots = utils.json.loads(new_slots)
    if not isinstance(new_slots, list):
        frappe.throw("new_slots should be list of new slots.")
    for slot in new_slots:
        starts_on = utils.get_datetime(slot["starts_on"])
        ends_on = utils.get_datetime(slot["ends_on"])
        if not starts_on or not ends_on:
            frappe.throw("Invalid new_slots")

    event_doc = frappe.get_doc(event_type, event_name)
    now_datetime = utils.now_datetime()
    if event_type == "Event":
        if event_doc.status != "Open":
            frappe.throw(f"Can not reschedule `{event_doc.status}` event.")
        if not event_doc.custom_sync_with_ms_calendar:
            frappe.throw(
                "Sync with Outlook if not enabled for the event, can not reschedule."
            )

        event_doc.set("status", "Cancelled")
        event_doc.append(
            "custom_outlook_reschedule_history",
            {
                "starts_on": event_doc.starts_on,
                "ends_on": event_doc.ends_on,
                "outlook_slot": event_doc.custom_outlook_from_slot,
                "rescheduled_by": frappe.session.user,
                "rescheduled_on": now_datetime,
            },
        )

        old_slot_doc = frappe.get_doc(
            "Outlook Event Slot", event_doc.custom_outlook_from_slot
        )
        event_slot_doc = frappe.get_doc(
            {
                "doctype": "Outlook Event Slot",
                "subject": event_doc.subject,
                "description": event_doc.description,
                "email_template": old_slot_doc.email_template,
                "reschedule_history": [
                    {
                        "rescheduled_by": ev_res_history.rescheduled_by,
                        "rescheduled_on": ev_res_history.rescheduled_on,
                    }
                    for ev_res_history in event_doc.custom_outlook_reschedule_history
                ],
                "event_participants": [
                    {
                        "reference_doctype": event_participant.reference_doctype,
                        "reference_docname": event_participant.reference_docname,
                        "email": event_participant.email,
                        "custom_participant_name": event_participant.custom_participant_name,
                        "custom_response": event_participant.custom_response,
                        "custom_response_time": event_participant.custom_response_time,
                        "custom_required": event_participant.custom_required,
                    }
                    for event_participant in event_doc.event_participants
                ],
                "slot_proposals": new_slots,
                "status": "Unconfirmed",
                "outlook_calendar": event_doc.custom_outlook_calendar,
                "organiser": event_doc.custom_outlook_organiser,
                "organiser_name": event_doc.custom_outlook_organiser_name,
                "color": event_doc.color,
                "event_location": event_doc.custom_outlook_location,
                "add_teams_meet": event_doc.custom_add_teams_meet,
                "all_day": event_doc.all_day,
                "repeat_this_event": event_doc.repeat_this_event,
                "repeat_on": event_doc.repeat_on,
                "repeat_till": event_doc.repeat_till,
            }
        )
        for week_field in WEEK_FIELDS:
            if event_doc.get(week_field):
                event_slot_doc.set(week_field, True)
        event_slot_doc = event_slot_doc.save()

        event_doc.set("custom_outlook_from_slot", event_slot_doc.name)
        event_doc.save()
    else:
        if event_doc.docstatus.is_submitted():
            frappe.throw("Event is already scheduled, can not update slots.")
        if event_doc.docstatus.is_cancelled():
            frappe.throw("Outlook Event Slot doc is cancelled, can not continue.")

        event_doc.set("slot_proposals", new_slots)
        event_doc.append(
            "reschedule_history",
            {"rescheduled_by": frappe.session.user, "rescheduled_on": now_datetime},
        )
        event_doc.save()

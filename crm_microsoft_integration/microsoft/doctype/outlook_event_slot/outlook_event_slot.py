# Copyright (c) 2025, OneHash and contributors
# For license information, please see license.txt

import frappe
from frappe import utils
from frappe.model.document import DocStatus
from frappe.website.website_generator import WebsiteGenerator
from crm_microsoft_integration.microsoft.customizations import event

WEEK_FIELDS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

MEETING_MODE_TAGS = {"ONLINE": " - Online", "IN_PERSON": " - In Person"}


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

    def validate_slots(self):
        pass

    def before_insert(self):
        self.validate_slots()

    def after_insert(self):
        self.db_set(
            {"route": f"slots/{self.name}", "published": 1},
            update_modified=False,
            notify=True,
            commit=True,
        )

    def confirm_event(self, slot_id, is_online, ignore_permissions=False):
        if self.selected_slot_start:
            frappe.throw("Event is already scheduled.")

        if is_online and not self.add_teams_meet:
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

        event_doc = self._prepare_event_doc(starts_on, ends_on, is_online)
        event_doc.save(ignore_permissions=ignore_permissions)

        self.update(
            {
                "status": "Confirmed",
                "selected_online": is_online,
                "selected_slot_start": starts_on,
                "selected_slot_end": ends_on,
                "docstatus": DocStatus.submitted(),
            }
        )
        self.save(ignore_permissions=True)

    def reschedule_event(self, new_slots, reschedule_reason):
        now_datetime = utils.now_datetime()

        if self.docstatus.is_submitted():
            frappe.throw("Event is already scheduled, can not update slots.")
        if self.docstatus.is_cancelled():
            frappe.throw("Outlook Event Slot doc is cancelled, can not continue.")

        self.set("slot_proposals", new_slots)
        self.append(
            "slot_reschedule_history",
            {
                "rescheduled_by": frappe.session.user,
                "rescheduled_on": now_datetime,
                "reschedule_reason": reschedule_reason,
            },
        )

    def cancel_event(self, cancel_reason):
        now_datetime = utils.now_datetime()

        if self.docstatus.is_submitted():
            frappe.throw("Event is already scheduled, can not cancel slots.")
        if self.docstatus.is_cancelled():
            frappe.throw("Outlook Event Slot doc is cancelled, can not continue.")

        self.append(
            "slot_reschedule_history",
            {
                "rescheduled_by": frappe.session.user,
                "rescheduled_on": now_datetime,
                "reschedule_reason": cancel_reason,
            },
        )

    def _prepare_event_doc(self, starts_on, ends_on, is_online):
        existing_event_name = frappe.db.exists(
            "Event", {"custom_outlook_from_slot": self.name}
        )
        event_doc = None

        if existing_event_name:
            event_doc = frappe.get_doc("Event", existing_event_name)
        else:
            event_doc = frappe.new_doc("Event")

        event_doc.update(
            {
                "status": "Open",
                "doctype": "Event",
                "custom_outlook_calendar": self.outlook_calendar,
                "custom_outlook_organiser": self.organiser,
                "custom_outlook_from_slot": self.name,
            }
        )

        # Subject updates to - Online or - In Person
        subject = event_doc.subject or self.subject
        for mode_tag in MEETING_MODE_TAGS:
            if subject.endswith(MEETING_MODE_TAGS[mode_tag]):
                subject = subject[: -len(MEETING_MODE_TAGS[mode_tag])]
                break
        if is_online:
            subject = subject + MEETING_MODE_TAGS["ONLINE"]
        else:
            subject = subject + MEETING_MODE_TAGS["IN_PERSON"]

        # Propagating reschedule history
        event_doc_reschedules = len(event_doc.custom_outlook_reschedule_history or [])
        for reschedule_history in self.reschedule_history:
            if reschedule_history.idx <= event_doc_reschedules:
                continue
            event_doc.append(
                "custom_outlook_reschedule_history",
                {
                    "starts_on": reschedule_history.starts_on,
                    "ends_on": reschedule_history.ends_on,
                    "outlook_slot": reschedule_history.outlook_slot,
                    "rescheduled_by": reschedule_history.rescheduled_by,
                    "rescheduled_on": reschedule_history.rescheduled_on,
                    "reschedule_reason": reschedule_history.reschedule_reason,
                },
            )

        event_doc = update_event_participants(
            event_doc, self.event_participants, self.users
        )
        event_doc.update(
            {
                "starts_on": starts_on,
                "ends_on": ends_on,
                "subject": subject,
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
        if is_online:
            event_doc.set("custom_add_teams_meet", True)
        elif self.event_location:
            event_doc.set("custom_add_teams_meet", False)
            event_doc.set("custom_outlook_location", self.event_location)

        for week_field in WEEK_FIELDS:
            if self.get("week_field"):
                event_doc.set(week_field, True)
            else:
                event_doc.set(week_field, False)

        return event_doc


def update_event_participants(doc, event_participants, users):
    new_participants = set()
    user_values = {}
    for p in event_participants:
        new_participants.add(
            (p.get("reference_doctype"), p.get("reference_docname"), p.get("email"))
        )
    for u in users:
        user_email, user_name = frappe.db.get_value(
            "User", u.get("user"), ["email", "full_name"]
        )
        user_values[u.get("user")] = (user_email, user_name)
        new_participants.add(("User", u.get("user"), user_email))

    existing_participants = list(doc.get("event_participants") or [])
    for participant in existing_participants:
        key = (
            participant.get("reference_doctype"),
            participant.get("reference_docname"),
            participant.get("email"),
        )
        if key not in new_participants:
            doc.remove(participant)

    participants = doc.get("event_participants") or []
    if doc.doctype == "Outlook Event Slot":
        participants += doc.get("users") or []
    existing_keys = {
        (
            p.get("reference_doctype", default="User"),
            p.get("reference_docname", default=p.get("user")),
            p.get(
                "email", default=user_values[p.get("user")][1] if p.get("user") else ""
            ),
        )
        for p in participants
    }

    for p in event_participants:
        key = (p.get("reference_doctype"), p.get("reference_docname"), p.get("email"))
        if key not in existing_keys:
            doc.append(
                "event_participants",
                {
                    "reference_doctype": p.get("reference_doctype"),
                    "reference_docname": p.get("reference_docname"),
                    "email": p.get("email"),
                    "custom_participant_name": p.get("custom_participant_name"),
                    "custom_required": p.get("custom_required"),
                },
            )
            existing_keys.add(key)
    for u in users:
        email, full_name = user_values[u.get("user")]
        key = ("User", u.get("user"), email)
        if key not in existing_keys:
            if doc.doctype == "Event":
                doc.append(
                    "event_participants",
                    {
                        "reference_doctype": "User",
                        "reference_docname": u.get("user"),
                        "email": email,
                        "custom_participant_name": full_name,
                    },
                )
            else:
                doc.append("users", {"user": u.get("user")})
            existing_keys.add(key)
    return doc


@frappe.whitelist()
def create_slot(doc):
    if isinstance(doc, str):
        doc = frappe.parse_json(doc)
    frappe.get_doc({"doctype": "Outlook Event Slot", **doc}).save()
    return "success"


@frappe.whitelist(allow_guest=True)
def confirm_slot(slot_id, mode_online):
    slot_name = frappe.db.get_value("Outlook Slot Proposals", slot_id, "parent")
    slot_doc = frappe.get_doc("Outlook Event Slot", slot_name)
    slot_doc.confirm_event(slot_id, frappe.parse_json(mode_online), True)


@frappe.whitelist()
def cancel_event(event_type, event_name, cancel_reason):
    if event_type not in ["Event", "Outlook Event Slot"]:
        frappe.throw("Invalid event_type")
    if not cancel_reason:
        frappe.throw("Cancel Reason is mandatory.")

    event_doc = frappe.get_doc(event_type, event_name)
    if event_type == "Event":
        event.cancel_event(event_doc, cancel_reason)
    else:
        event_doc.cancel_event(cancel_reason)
    event_doc.save()


@frappe.whitelist()
def reschedule_event_slots(event_type, event_name, new_slots, reschedule_reason):
    if event_type not in ["Event", "Outlook Event Slot"]:
        frappe.throw("Invalid event_type")
    if not reschedule_reason:
        frappe.throw("Reschedule Reason is mandatory.")

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
    if event_type == "Event":
        event.rescheudle_event(event_doc, new_slots, reschedule_reason)
    else:
        event_doc.reschedule_event(new_slots, reschedule_reason)
    event_doc.save()


@frappe.whitelist()
def edit_event(
    event_type,
    event_name,
    subject,
    description,
    add_teams_meet,
    event_location,
    event_participants,
    users,
):
    if event_type not in ["Event", "Outlook Event Slot"]:
        frappe.throw("Invalid event_type")

    add_teams_meet = frappe.parse_json(add_teams_meet)
    event_participants = frappe.parse_json(event_participants)
    users = frappe.parse_json(users)

    event_doc = frappe.get_doc(event_type, event_name)

    if event_type == "Event":
        event_doc.update(
            {
                "subject": subject,
                "description": description,
                "custom_add_teams_meet": add_teams_meet,
                "custom_outlook_location": event_location,
            }
        )
    else:
        event_doc.update(
            {
                "subject": subject,
                "description": description,
                "add_teams_meet": add_teams_meet,
                "event_location": event_location,
            }
        )
    event_doc = update_event_participants(event_doc, event_participants, users)
    event_doc.save()

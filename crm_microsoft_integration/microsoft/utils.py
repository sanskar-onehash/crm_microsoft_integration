import frappe
from frappe import utils
from frappe.query_builder.functions import IfNull
from pypika import Order


@frappe.whitelist()
def get_reference_events(ref_doctype, ref_docname):
    parent_doctypes = ["Event", "Outlook Event Slot"]

    EventParticipants = frappe.qb.DocType("Event Participants")
    EventParticipantsAttendees = frappe.qb.DocType("Event Participants")
    Event = frappe.qb.DocType("Event")
    EventSlot = frappe.qb.DocType("Outlook Event Slot")

    events = (
        frappe.qb.from_(EventParticipants)
        .join(EventParticipantsAttendees)
        .on(EventParticipants.parent == EventParticipantsAttendees.parent)
        .left_join(Event)
        .on(Event.name == EventParticipants.parent)
        .left_join(EventSlot)
        .on(EventSlot.name == EventParticipants.parent)
        .select(
            EventParticipantsAttendees.parenttype.as_("type"),
            EventParticipantsAttendees.parent.as_("name"),
            EventParticipantsAttendees.reference_doctype,
            EventParticipantsAttendees.reference_docname,
            EventParticipantsAttendees.email,
            EventParticipantsAttendees.custom_participant_name,
            EventParticipantsAttendees.custom_required,
            EventParticipants.parenttype.as_("type"),
            EventParticipants.parent.as_("name"),
            EventParticipants.reference_doctype,
            EventParticipants.reference_docname,
            EventParticipants.email,
            EventParticipants.custom_participant_name,
            EventParticipants.custom_required,
            IfNull(EventSlot.status, "Confirmed").as_("status"),
            IfNull(EventSlot.subject, Event.subject).as_("subject"),
            IfNull(EventSlot.description, Event.description).as_("description"),
            IfNull(EventSlot.organiser_name, Event.custom_outlook_organiser_name).as_(
                "organiser"
            ),
            IfNull(EventSlot.event_location, Event.custom_outlook_location).as_(
                "location"
            ),
            IfNull(EventSlot.add_teams_meet, Event.custom_add_teams_meet).as_(
                "is_online"
            ),
            IfNull(EventSlot.creation, Event.creation).as_("creation"),
            Event.custom_outlook_meeting_link.as_("meeting_link"),
            Event.starts_on,
            Event.ends_on,
            Event.status.as_("event_status"),
        )
        .where(
            (EventParticipants.reference_doctype == ref_doctype)
            & (EventParticipants.reference_docname == ref_docname)
            & (EventParticipants.parenttype.isin(parent_doctypes))
            & (EventParticipants.parentfield == "event_participants")
        )
        .orderby("creation", order=Order.desc)
    ).run(as_dict=True)

    # Slot Proposals
    event_slots = {
        event.name
        for event in events
        if event.type == "Outlook Event Slot" and event.status != "Confirmed"
    }
    proposed_slots = frappe.db.get_all(
        "Outlook Slot Proposals",
        {
            "parent": ["in", list(event_slots)],
            "parenttype": "Outlook Event Slot",
            "parentfield": "slot_proposals",
        },
        ["parent", "starts_on", "ends_on"],
    )
    event_slot_wise_proposed_slots = {}
    for proposed_slot in proposed_slots:
        if proposed_slot.parent not in event_slot_wise_proposed_slots:
            event_slot_wise_proposed_slots[proposed_slot.parent] = []

        event_slot_wise_proposed_slots[proposed_slot.parent].append(
            {"starts_on": proposed_slot.starts_on, "ends_on": proposed_slot.ends_on}
        )

    now_datetime = utils.now_datetime()
    have_upcoming_events = False
    grouped_events = []
    last_event = None
    for event in events:
        if event.type == "Outlook Event Slot" and event.status == "Confirmed":
            continue

        if (
            not have_upcoming_events
            and event.starts_on
            and event.starts_on > now_datetime
        ):
            have_upcoming_events = True

        if last_event and last_event["name"] != event.name:
            grouped_events.append(last_event)
            last_event = None

        if not last_event:
            is_cancelled = event.event_status and event.event_status == "Cancelled"
            can_reschedule = not is_cancelled and (
                event.starts_on > now_datetime if event.starts_on else True
            )  # True for slots
            can_cancel = can_reschedule or event.event_status == "Open"
            last_event = {
                "type": event.type,
                "name": event.name,
                "starts_on": event.starts_on,
                "ends_on": event.ends_on,
                "subject": event.subject,
                "description": event.description,
                "organiser": event.organiser,
                "location": event.location,
                "is_online": event.is_online,
                "meeting_link": event.meeting_link,
                "creation": event.creation,
                "participants": [],
                # TODO: There can be an offset limit for rescheduling
                "can_reschedule": can_reschedule,
                "can_cancel": can_cancel,
                "is_cancelled": is_cancelled,
            }

            if event.type == "Outlook Event Slot":
                last_event["slots"] = event_slot_wise_proposed_slots[event.name]

        participant = {
            "ref_doctype": event.reference_doctype,
            "ref_docname": event.reference_docname,
            "email": event.email,
            "participant_name": event.custom_participant_name,
            "is_required": event.custom_required,
        }
        if participant not in last_event["participants"]:
            last_event["participants"].append(participant)
    if last_event and last_event not in grouped_events:
        grouped_events.append(last_event)
    return {"events": grouped_events, "have_upcoming_events": have_upcoming_events}

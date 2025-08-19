import frappe
import copy


@frappe.whitelist()
def get_reference_events(ref_doctype, ref_docname, with_slots=False):
    events = get_scheduled_events(ref_doctype, ref_docname)
    for e in events:
        e["type"] = "event"
        e["time_slots"] = [
            {"starts_on": e.pop("starts_on"), "ends_on": e.pop("ends_on")}
        ]

    slots = get_scheduled_slots(ref_doctype, ref_docname) if with_slots else []
    for s in slots:
        s["type"] = "slot"

    combined = sorted(events + slots, key=lambda x: x["creation"])

    grouped = {}
    for item in combined:
        name = item["name"]
        if name not in grouped:
            new_item = copy.deepcopy(item)
            new_item["time_slots"] = [
                {"starts_on": item.pop("starts_on"), "ends_on": item.pop("ends_on")}
            ]
            grouped[name] = new_item
        else:
            grouped[name]["time_slots"].append(
                {"starts_on": item["starts_on"], "ends_on": item["ends_on"]}
            )

    return list(grouped.values())


def get_scheduled_events(ref_doctype, ref_docname):
    event = frappe.qb.DocType("Event")
    event_participants = frappe.qb.DocType("Event Participants")

    query = (
        frappe.qb.from_(event)
        .join(event_participants)
        .on(event_participants.parent == event.name)
        .select(
            event.name,
            event.subject,
            event.event_category,
            event.starts_on,
            event.ends_on,
            event.status,
            event.custom_outlook_meeting_link,
            event.description,
            event.creation,
        )
        .where(
            (event_participants.reference_doctype == ref_doctype)
            & (event_participants.reference_docname == ref_docname)
        )
        .orderby(event.creation)
    )
    scheduled_events = query.run(as_dict=True)

    return scheduled_events


def get_scheduled_slots(ref_doctype, ref_docname):
    slot = frappe.qb.DocType("Outlook Event Slot")
    event_participants = frappe.qb.DocType("Event Participants")
    proposed_slots = frappe.qb.DocType("Outlook Slot Proposals")

    query = (
        frappe.qb.from_(slot)
        .join(event_participants)
        .on(event_participants.parent == slot.name)
        .join(proposed_slots)
        .on(proposed_slots.parent == slot.name)
        .select(
            slot.name,
            slot.subject,
            slot.status,
            slot.add_teams_meet,
            slot.event_location,
            slot.description,
            slot.creation,
            proposed_slots.starts_on,
            proposed_slots.ends_on,
        )
        .where(
            (event_participants.reference_doctype == ref_doctype)
            & (event_participants.reference_docname == ref_docname)
        )
        .orderby(slot.creation)
    )
    scheduled_slots = query.run(as_dict=True)

    return scheduled_slots

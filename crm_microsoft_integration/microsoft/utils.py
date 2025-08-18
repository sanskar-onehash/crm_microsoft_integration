import frappe


@frappe.whitelist()
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
        )
        .where(
            (event_participants.reference_doctype == ref_doctype)
            & (event_participants.reference_docname == ref_docname)
        )
        .orderby(event.creation)
    )
    scheduled_events = query.run(as_dict=True)

    return scheduled_events

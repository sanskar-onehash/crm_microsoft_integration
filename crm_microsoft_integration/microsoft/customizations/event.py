import frappe
from frappe import _, utils
from crm_microsoft_integration.microsoft.integration.event import event

SYNC_OUTLOOK_EVENT_TIMEOUT = 25 * 60
SYNC_OUTLOOK_EVENT_JOB_NAME = "sync_outlook_events"
SYNC_OUTLOOK_EVENT_PROGRESS_ID = "sync_outlook_events_progress"


def event_after_insert(doc, method=None):
    if (
        not doc.custom_sync_with_ms_calendar
        or doc.custom_is_outlook_event
        or not frappe.db.exists(
            "Outlook Calendar", {"name": doc.custom_outlook_calendar}
        )
    ):
        return

    outlook_calendar = frappe.get_doc("Outlook Calendar", doc.custom_outlook_calendar)
    if not outlook_calendar.push_to_outlook_calendar:
        return

    microsoft_user_doc = frappe.get_doc("Microsoft User", doc.custom_outlook_organiser)
    outlook_event, missing_email_participants = event.insert_cal_event(
        doc, microsoft_user_doc, outlook_calendar
    )

    if missing_email_participants:
        frappe.msgprint(
            _(
                "Outlook Calendar - Participant email not found. Did not add attendee for -<br>{0}"
            ).format(
                "<br>".join(
                    f"{d.get('participant_name')} {d.get('ref_dt')} {d.get('ref_dn')}"
                    for d in missing_email_participants
                )
            ),
            alert=True,
            indicator="yellow",
        )

    check_and_set_updates_to_db(doc, outlook_event)


def event_on_update(doc, method=None):
    if (
        doc.is_new()
        or not doc.custom_sync_with_ms_calendar
        or doc.custom_is_outlook_event
        or not frappe.db.exists(
            "Outlook Calendar", {"name": doc.custom_outlook_calendar}
        )
    ):
        return

    if doc.custom_sync_with_ms_calendar and not doc.custom_outlook_event_id:
        # If custom_sync_with_ms_calendar is checked later, then insert the event rather than updating it.
        event_after_insert(doc)
        return

    outlook_calendar = frappe.get_doc("Outlook Calendar", doc.custom_outlook_calendar)
    if not outlook_calendar.push_to_outlook_calendar:
        return

    microsoft_user_doc = frappe.get_doc("Microsoft User", doc.custom_outlook_organiser)
    outlook_event, missing_email_participants = event.update_cal_event(
        doc, microsoft_user_doc, outlook_calendar
    )

    if missing_email_participants:
        frappe.msgprint(
            _(
                "Outlook Calendar - Participant email not found. Did not add attendee for -<br>{0}"
            ).format(
                "<br>".join(
                    f"{d.get('participant_name')} {d.get('ref_dt')} {d.get('ref_dn')}"
                    for d in missing_email_participants
                )
            ),
            alert=True,
            indicator="yellow",
        )

    check_and_set_updates_to_db(doc, outlook_event)


def event_on_trash(doc, method=None):
    if (
        not doc.custom_sync_with_ms_calendar
        or doc.custom_is_outlook_event
        or not frappe.db.exists(
            "Outlook Calendar", {"name": doc.custom_outlook_calendar}
        )
    ):
        return

    outlook_calendar = frappe.get_doc("Outlook Calendar", doc.custom_outlook_calendar)
    if not outlook_calendar.push_to_outlook_calendar:
        return

    delete_res = event.delete_cal_event(
        doc.custom_outlook_event_id, doc.custom_outlook_organiser, outlook_calendar.id
    )

    if delete_res != "success":
        frappe.msgprint(
            _("Outlook Server responded with: {0}").format(delete_res),
            alert=True,
            indicator="yellow",
        )


def check_and_set_updates_to_db(event_doc, new_event):
    new_updates = {}
    for fieldname, new_value in new_event.items():
        old_value = event_doc.get(fieldname)

        if isinstance(new_value, utils.datetime.datetime):
            old_value_dt = utils.get_datetime(old_value)
            if old_value_dt != new_value:
                new_updates[fieldname] = utils.get_datetime_str(new_value)

        elif old_value != new_value:
            new_updates[fieldname] = new_value

    if new_updates:
        event_doc.db_set(
            new_updates,
            update_modified=False,
            notify=True,
            commit=True,
        )


@frappe.whitelist()
def sync_outlook_events():
    frappe.enqueue(
        _sync_outlook_events,
        queue="default",
        timeout=SYNC_OUTLOOK_EVENT_TIMEOUT,
        job_name=SYNC_OUTLOOK_EVENT_JOB_NAME,
    )
    return {
        "status": "success",
        "msg": "Outlook Events syncing started in background.",
        "track_on": SYNC_OUTLOOK_EVENT_PROGRESS_ID,
    }


def _sync_outlook_events():
    ms_users = frappe.db.get_list("Microsoft User", ["name"])
    user_ids = [ms_user.name for ms_user in ms_users]

    outlook_events = event.get_users_events(user_ids)
    total_events = len(outlook_events)

    for idx, user in enumerate(outlook_events):
        frappe.publish_realtime(
            SYNC_OUTLOOK_EVENT_PROGRESS_ID,
            {
                "progress": idx + 1,
                "total": total_events,
                "title": "Syncing Outlook Events",
            },
        )

        for outlook_event in outlook_events[user]:
            participants = outlook_event.pop("event_participants")
            existing_event = frappe.db.exists(
                "Event",
                {"custom_outlook_event_id": outlook_event["custom_outlook_event_id"]},
            )

            if existing_event:
                event_doc = frappe.get_doc("Event", existing_event)
                has_updated = False

                for fieldname, new_value in outlook_event.items():
                    old_value = event_doc.get(fieldname)

                    if old_value != new_value:
                        event_doc.set(fieldname, new_value)
                        has_updated = True

                if has_updated:
                    event_doc.save()
            else:
                frappe.get_doc(
                    {
                        "doctype": "Event",
                        "custom_is_outlook_event": True,
                        "custom_sync_with_ms_calendar": True,
                        "custom_add_teams_meet": (
                            True
                            if outlook_event["custom_outlook_meeting_link"]
                            else False
                        ),
                        **outlook_event,
                    }
                ).save()
    frappe.db.commit()

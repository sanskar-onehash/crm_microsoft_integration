import frappe
from frappe import _, utils
from crm_microsoft_integration.microsoft.integration.event import event

SYNC_OUTLOOK_EVENT_TIMEOUT = 25 * 60
SYNC_OUTLOOK_EVENT_JOB_NAME = "sync_outlook_events"
SYNC_OUTLOOK_EVENT_PROGRESS_ID = "sync_outlook_events_progress"

WEEK_FIELDS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def event_after_insert(doc, method=None):
    if doc.custom_is_outlook_event or not doc.custom_sync_with_ms_calendar:
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
    if doc.is_new() or not (
        doc.custom_sync_with_ms_calendar or doc.custom_is_outlook_event
    ):
        return

    old_doc = doc.get_doc_before_save()

    if doc.custom_sync_with_ms_calendar and (
        not doc.custom_outlook_event_id
        or (old_doc.status == "Cancelled" and doc.status != "Cancelled")
    ):
        # If custom_sync_with_ms_calendar is checked later, then insert the event rather than updating it.
        # Or if event was previously cancelled
        event_after_insert(doc)
        return

    outlook_calendar = frappe.get_doc("Outlook Calendar", doc.custom_outlook_calendar)
    if not outlook_calendar.push_to_outlook_calendar:
        return

    if doc.status == "Cancelled":
        if not len(doc.custom_outlook_reschedule_history):
            frappe.throw("Reschedule history not maintained")
        cancellation_reason = doc.custom_outlook_reschedule_history[
            len(doc.custom_outlook_reschedule_history) - 1
        ].reschedule_reason
        event.cancel_cal_event(
            doc.custom_outlook_event_id,
            doc.custom_outlook_organiser,
            cancellation_reason,
            outlook_calendar.id,
        )
    else:
        microsoft_user_doc = frappe.get_doc(
            "Microsoft User", doc.custom_outlook_organiser
        )
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


def cancel_event(doc, cancel_reason):
    if doc.status != "Open":
        frappe.throw(f"Can not cancel `{doc.status}` event.")
    if not doc.custom_sync_with_ms_calendar:
        frappe.throw(
            "Sync with Outlook if not enabled for the event, can not reschedule."
        )

    doc.set("status", "Cancelled")
    doc.append(
        "custom_outlook_reschedule_history",
        {
            "starts_on": doc.starts_on,
            "ends_on": doc.ends_on,
            "outlook_slot": doc.custom_outlook_from_slot,
            "rescheduled_by": frappe.session.user,
            "rescheduled_on": utils.now_datetime(),
            "reschedule_reason": cancel_reason,
        },
    )
    doc.save()


def rescheudle_event(doc, new_slots, reschedule_reason):
    if doc.status != "Open":
        frappe.throw(f"Can not reschedule `{doc.status}` event.")
    if not doc.custom_sync_with_ms_calendar:
        frappe.throw(
            "Sync with Outlook if not enabled for the event, can not reschedule."
        )

    doc.set("status", "Cancelled")
    doc.append(
        "custom_outlook_reschedule_history",
        {
            "starts_on": doc.starts_on,
            "ends_on": doc.ends_on,
            "outlook_slot": doc.custom_outlook_from_slot,
            "rescheduled_by": frappe.session.user,
            "rescheduled_on": utils.now_datetime(),
            "reschedule_reason": reschedule_reason,
        },
    )

    old_slot_doc = frappe.get_doc("Outlook Event Slot", doc.custom_outlook_from_slot)
    event_participants = []
    users = []
    for event_participant in doc.event_participants:
        if event_participant.reference_doctype == "User":
            users.append({"user": event_participant.reference_docname})
        else:
            event_participants.append(
                {
                    "reference_doctype": event_participant.reference_doctype,
                    "reference_docname": event_participant.reference_docname,
                    "email": event_participant.email,
                    "custom_participant_name": event_participant.custom_participant_name,
                    "custom_response": event_participant.custom_response,
                    "custom_response_time": event_participant.custom_response_time,
                    "custom_required": event_participant.custom_required,
                }
            )

    event_slot_doc = frappe.get_doc(
        {
            "doctype": "Outlook Event Slot",
            "subject": doc.subject,
            "description": doc.description,
            "email_template": old_slot_doc.email_template,
            "reschedule_history": [
                {
                    "starts_on": ev_res_history.starts_on,
                    "ends_on": ev_res_history.ends_on,
                    "outlook_slot": ev_res_history.outlook_slot,
                    "rescheduled_by": ev_res_history.rescheduled_by,
                    "rescheduled_on": ev_res_history.rescheduled_on,
                    "reschedule_reason": reschedule_reason,
                }
                for ev_res_history in doc.custom_outlook_reschedule_history
            ],
            "event_participants": event_participants,
            "users": users,
            "slot_proposals": new_slots,
            "status": "Unconfirmed",
            "outlook_calendar": doc.custom_outlook_calendar,
            "organiser": doc.custom_outlook_organiser,
            "organiser_name": doc.custom_outlook_organiser_name,
            "color": doc.color,
            "event_location": doc.custom_outlook_location
            or old_slot_doc.event_location,
            "add_teams_meet": doc.custom_add_teams_meet or old_slot_doc.add_teams_meet,
            "all_day": doc.all_day,
            "repeat_this_event": doc.repeat_this_event,
            "repeat_on": doc.repeat_on,
            "repeat_till": doc.repeat_till,
        }
    )
    for week_field in WEEK_FIELDS:
        if doc.get(week_field):
            event_slot_doc.set(week_field, True)
    event_slot_doc = event_slot_doc.save()

    doc.set("custom_outlook_from_slot", event_slot_doc.name)


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
            existing_event = frappe.db.exists(
                "Event",
                {"custom_outlook_event_id": outlook_event["custom_outlook_event_id"]},
            )

            if existing_event:
                event_doc = frappe.get_doc("Event", existing_event)
                check_and_set_updates_to_db(
                    event_doc, outlook_event, update_modified=True, commit=False
                )
            else:
                participants = outlook_event.pop("event_participants")
                event_doc = frappe.get_doc(
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
                check_and_set_participants_updates_to_db(
                    event_doc, participants, update_modified=True, commit=False
                )
    frappe.db.commit()


def check_and_set_updates_to_db(
    old_doc,
    new_values,
    update_modified=False,
    notify=True,
    commit=True,
):
    new_updates = {}
    for fieldname, new_value in new_values.items():
        old_value = old_doc.get(fieldname)

        if fieldname == "event_participants":
            check_and_set_participants_updates_to_db(
                old_doc,
                new_value,
                update_modified=update_modified,
                notify=notify,
                commit=commit,
            )

        elif isinstance(new_value, utils.datetime.datetime):
            old_value_dt = utils.get_datetime(old_value)
            if old_value_dt != new_value:
                new_updates[fieldname] = utils.get_datetime_str(new_value)

        elif old_value != new_value:
            new_updates[fieldname] = new_value

    if new_updates:
        old_doc.db_set(
            new_updates,
            update_modified=update_modified,
            notify=notify,
            commit=commit,
        )


def check_and_set_participants_updates_to_db(
    event_doc,
    outlook_participants,
    update_modified=False,
    notify=True,
    commit=True,
):
    prev_doc_participants = {
        participant.email: participant for participant in event_doc.event_participants
    }
    prev_outlook_particpants = {
        participant.email: participant
        for participant in event_doc.custom_outlook_participants
    }
    next_outlook_idx = len(prev_outlook_particpants) + 1

    for new_participant in outlook_participants or []:
        new_participant_email = new_participant.get("email")
        if new_participant_email in prev_doc_participants:
            check_and_set_updates_to_db(
                prev_doc_participants[new_participant_email],
                outlook_partcipant_to_event(new_participant),
                update_modified=update_modified,
                notify=notify,
                commit=commit,
            )
        elif new_participant_email in prev_outlook_particpants:
            check_and_set_updates_to_db(
                prev_outlook_particpants[new_participant_email],
                new_participant,
                update_modified=update_modified,
                notify=notify,
                commit=commit,
            )
        else:
            frappe.get_doc(
                {
                    "doctype": "Outlook Event Participants",
                    "parent": event_doc.name,
                    "parenttype": event_doc.doctype,
                    "parentfield": "custom_outlook_participants",
                    "idx": next_outlook_idx,
                    **new_participant,
                }
            ).save(ignore_permissions=True)
            next_outlook_idx += 1


def outlook_partcipant_to_event(outlook_participant):
    return {
        "email": outlook_participant.get("email"),
        "custom_participant_name": outlook_participant.get("participant_name"),
        "custom_required": outlook_participant.get("is_required"),
        "custom_response": outlook_participant.get("response"),
        "custom_response_time": outlook_participant.get("response_time"),
    }

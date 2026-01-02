import pytz
from frappe import utils


def parse_events_res(events_res):
    parsed_events = []

    for event in events_res["value"]:
        parsed_events.append(parse_event_res(event))
    return parsed_events


def parse_event_res(event_res):
    event_participants = []
    for attendee in event_res["attendees"]:
        event_participants.append(
            {
                "is_required": attendee["type"] == "required",
                "response": attendee["status"]["response"],
                "response_time": parse_outlook_date(attendee["status"]["time"]),
                "participant_name": attendee["emailAddress"]["name"],
                "email": attendee["emailAddress"]["address"],
            }
        )
    return {
        "custom_outlook_event_id": event_res["id"],
        "starts_on": parse_outlook_date_object(event_res["start"]),
        "ends_on": parse_outlook_date_object(event_res["end"]),
        "custom_outlook_change_key": event_res["changeKey"],
        "custom_outlook_event_uid": event_res["iCalUId"],
        "subject": event_res["subject"],
        "all_day": event_res["isAllDay"],
        "custom_outlook_event_link": event_res["webLink"],
        "description": event_res["body"]["content"],
        # "organiser_email": event_res["organizer"]["emailAddress"]["address"],
        "custom_outlook_meeting_link": (
            event_res["onlineMeeting"]["joinUrl"]
            if event_res["onlineMeeting"]
            else None
        ),
        "custom_outlook_location_address": parse_location_address_to_html(
            event_res["location"].get("address") or {}
        ),
        "event_participants": event_participants,
    }


def outlook_event_from_event_doc(event_doc, organizer_doc=None, calendar_doc=None):
    is_online_meeting = event_doc.custom_add_teams_meet
    attendees, email_not_found = get_outlook_attendees_from_event(event_doc)
    organizer = get_outlook_organizer_from_user(organizer_doc)

    return {
        "subject": event_doc.subject,
        "attendees": attendees,
        "allowNewTimeProposals": bool(event_doc.custom_ms_allow_new_time_proposals),
        "body": {
            "contentType": "HTML",
            "content": event_doc.description,
        },
        "changeKey": event_doc.custom_outlook_change_key,
        "createdDateTime": format_datetime_to_utc_iso(event_doc.creation),
        "lastModifiedDateTime": format_datetime_to_utc_iso(event_doc.modified),
        "start": format_date_for_outlook(event_doc.starts_on),
        "end": format_date_for_outlook(event_doc.ends_on),
        "iCalUId": event_doc.custom_outlook_event_uid,
        "id": event_doc.custom_outlook_event_id,
        "isAllDay": bool(event_doc.all_day),
        "isOnlineMeeting": bool(is_online_meeting),
        "onlineMeetingProvider": ("teamsForBusiness" if is_online_meeting else None),
        "onlineMeeting": {
            "joinUrl": (
                event_doc.custom_outlook_meeting_link if is_online_meeting else None
            )
        },
        "location": {
            "displayName": event_doc.custom_outlook_location,
            "locationType": "default",
        },
        "isOrganizer": calendar_doc
        and event_doc.custom_outlook_organiser == calendar_doc.microsoft_user,
        "organizer": organizer,
        "showAs": "busy",
        "type": "singleInstance",
        "webLink": event_doc.custom_outlook_event_link,
        "responseStatus": {
            "response": "organizer",
            "time": format_datetime_to_utc_iso(event_doc.creation),
        },
    }, email_not_found


def get_outlook_attendees_from_event(event_doc):
    attendees, email_not_found = [], []

    for participant in event_doc.event_participants:
        if participant.get("email"):
            attendees.append(
                {
                    "emailAddress": {
                        "address": participant.email,
                        "name": participant.custom_participant_name,
                    }
                }
            )
        else:
            email_not_found.append(
                {
                    "ref_dt": participant.reference_doctype,
                    "ref_dn": participant.reference_docname,
                    "participant_name": participant.custom_participant_name,
                }
            )

    return attendees, email_not_found


def get_outlook_organizer_from_user(organizer_user_doc=None):
    if organizer_user_doc:
        return {
            "emailAddress": {
                "name": organizer_user_doc.display_name,
                "address": organizer_user_doc.mail or organizer_user_doc.principal_name,
            }
        }
    return None


def parse_location_address_to_html(address):
    address_html = "<div>"
    for key in address:
        address_html = address_html + f"<p><strong>{key}:</strong> {address[key]}</p>"
    address_html = address_html + "</div>"
    return address_html


def format_date_for_outlook(datetime):
    return {
        "dateTime": utils.get_datetime(datetime).isoformat(),
        "timeZone": utils.get_system_timezone(),
    }


def parse_outlook_date_object(datetime_obj):
    iso_datetime_str = datetime_obj.get("dateTime")
    datetime_tz = datetime_obj.get("timeZone")
    if not iso_datetime_str:
        raise ValueError("Missing 'dateTime' in input object")
    if not datetime_tz:
        raise ValueError("Missing 'timeZone' in input object")

    parsed_datetime = pytz.timezone(datetime_tz).localize(
        utils.get_datetime(iso_datetime_str)
    )

    return parse_outlook_date(parsed_datetime)


def format_datetime_to_utc_iso(datetime_obj):
    return (
        utils.get_datetime(datetime_obj)
        .astimezone(pytz.UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_outlook_date(datetime_like_obj):
    system_tz_name = utils.get_system_timezone()
    system_tz = pytz.timezone(system_tz_name)

    datetime = utils.get_datetime(datetime_like_obj)
    if datetime:
        return datetime.astimezone(system_tz).replace(tzinfo=None)
    return None

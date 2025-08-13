import pytz
from dateutil import parser
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
                "custom_required": attendee["type"] == "required",
                "custom_response": attendee["status"]["response"],
                "custom_response_time": attendee["status"]["time"],
                "custom_participant_name": attendee["emailAddress"]["name"],
                "email": attendee["emailAddress"]["address"],
            }
        )
    return {
        "id": event_res["id"],
        "starts_on": parse_outlook_date(event_res["start"]),
        "ends_on": parse_outlook_date(event_res["end"]),
        "change_key": event_res["changeKey"],
        "custom_outlook_event_id": event_res["iCalUId"],
        "subject": event_res["subject"],
        "all_day": event_res["isAllDay"],
        "custom_outlook_event_link": event_res["webLink"],
        "description": event_res["body"]["content"],
        "organiser_email": event_res["organizer"]["emailAddress"]["address"],
        "custom_outlook_meeting_link": (
            event_res["onlineMeeting"]["joinUrl"]
            if event_res["onlineMeeting"]
            else None
        ),
        "custom_outlook_location_address": utils.json.dumps(
            event_res["location"].get("address") or ""
        ),
        "event_participants": event_participants,
    }


def outlook_event_from_event_doc(event_doc, calendar_doc=None):
    is_online_meeting = event_doc.custom_add_teams_meet
    attendees, email_not_found = get_attendees_from_event(event_doc)
    return {
        "subject": event_doc.subject,
        "attendees": attendees,
        "body": {"contentType": "html", "content": event_doc.description},
        "changeKey": event_doc.custom_outlook_change_key,
        "createdDateTime": format_datetime_to_utc(event_doc.creation),
        "lastModifiedDateTime": format_datetime_to_utc(event_doc.modified),
        "start": format_date_for_outlook(event_doc.starts_on),
        "end": format_date_for_outlook(event_doc.ends_on),
        "iCalUId": event_doc.custom_outlook_event_uid,
        "id": event_doc.custom_outlook_event_id,
        "isAllDay": event_doc.all_day,
        "isOnlineMeeting": is_online_meeting,
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
        "organizer": event_doc.custom_outlook_organiser,
        "recurrence": False,
        "showAs": "busy",
        "type": "singleInstance",
        "webLink": event_doc.custom_outlook_event_link,
        "responseStatus": {"response": "organizer", "time": event_doc.creation},
    }, email_not_found


def get_attendees_from_event(event_doc):
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


def format_date_for_outlook(datetime):
    return {
        "dateTime": utils.get_datetime(datetime).isoformat(),
        "timeZone": utils.get_system_timezone(),
    }


def parse_outlook_date(datetime_obj):
    iso_datetime_str = datetime_obj.get("dateTime")
    if not iso_datetime_str:
        raise ValueError("Missing 'dateTime' in input object")

    parsed_datetime = parser.isoparse(iso_datetime_str)

    system_tz_name = utils.get_system_timezone()
    system_tz = pytz.timezone(system_tz_name)

    converted_datetime = parsed_datetime.astimezone(system_tz)

    return converted_datetime.replace(tzinfo=None)


def format_datetime_to_utc(datetime_obj):
    return utils.get_datetime(datetime_obj).astimezone(pytz.UTC)

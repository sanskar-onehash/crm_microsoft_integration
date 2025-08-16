from requests.exceptions import HTTPError
from crm_microsoft_integration.microsoft.integration.event import api, utils


def get_users_events(users, calendar_events=False, calendar_id=None, group_id=None):
    user_wise_events = {}
    for user in users:
        try:
            user_wise_events[user] = get_user_events(
                user, calendar_events, calendar_id, group_id
            )
        except HTTPError as e:
            if e.response.status_code == 404:
                user_wise_events[user] = []
    return user_wise_events


def get_user_events(user, calendar_events=False, calendar_id=None, group_id=None):
    events_res = api.get_user_events(user, calendar_events, calendar_id, group_id)
    return utils.parse_events_res(events_res)


def insert_cal_event(event_doc, orgainzer_user_doc, calendar_doc):
    outlook_event, missing_email_participants = utils.outlook_event_from_event_doc(
        event_doc, orgainzer_user_doc, calendar_doc
    )
    event_res = api.create_user_event(
        outlook_event, event_doc.custom_outlook_organiser, calendar_id=calendar_doc.id
    )
    event = utils.parse_event_res(event_res)

    return event, missing_email_participants


def update_cal_event(event_doc, orgainzer_user_doc, calendar_doc):
    outlook_event, missing_email_participants = utils.outlook_event_from_event_doc(
        event_doc, orgainzer_user_doc, calendar_doc
    )

    event_res = api.update_user_event(
        outlook_event, event_doc.custom_outlook_organiser, calendar_id=calendar_doc.id
    )
    event = utils.parse_event_res(event_res)

    return event, missing_email_participants


def delete_cal_event(event_id, user_id, calendar_id=None):
    try:
        api.delete_user_event(event_id, user_id, calendar_id=calendar_id)
        return "success"
    except HTTPError as e:
        if e.response.status_code == 404:
            # Prevent raise error if event already deleted
            return "Event not found"
        else:
            raise e

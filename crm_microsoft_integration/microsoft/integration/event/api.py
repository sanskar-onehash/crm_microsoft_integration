import frappe
from crm_microsoft_integration.microsoft.integration import utils, config

ENDPOINT_BASE = "/users"
EVENTS_ENDPOINT = "/events"


def get_user_events(user_id, calendar_events=False, calendar_id=None, group_id=None):
    if group_id and not calendar_id:
        frappe.throw("Calendar ID is needed with Group ID")

    events_endpoint = f"{ENDPOINT_BASE}/{user_id}"
    if calendar_id or calendar_events:
        events_endpoint = (
            events_endpoint
            + f"{f'/calendarGroups/{group_id}' if group_id else ''}/calendar{f's/{calendar_id}' if calendar_id else ''}"
        )

    events_endpoint = events_endpoint + EVENTS_ENDPOINT

    return utils.make_get_request(config.GRAPH_BASE_URI, events_endpoint)


def create_user_event(event, user_id, calendar_events=False, calendar_id=None):
    events_endpoint = f"{ENDPOINT_BASE}/{user_id}"
    if calendar_id or calendar_events:
        events_endpoint += f"/calendar{f's/{calendar_id}' if calendar_id else ''}"

    events_endpoint += EVENTS_ENDPOINT

    return utils.make_post_request(config.GRAPH_BASE_URI, events_endpoint, json=event)


def update_user_event(
    event, user_id, calendar_events=False, calendar_id=None, group_id=None
):
    events_endpoint = f"{ENDPOINT_BASE}/{user_id}"
    if calendar_id or calendar_events:
        events_endpoint += f"{f'/calendarGroups/{group_id}' if group_id else ''}/calendar{f's/{calendar_id}' if calendar_id else ''}"

    events_endpoint += EVENTS_ENDPOINT + f"/{event['id']}"

    return utils.make_patch_request(config.GRAPH_BASE_URI, events_endpoint, json=event)


def delete_user_event(
    event_id, user_id, calendar_events=False, calendar_id=None, group_id=None
):
    events_endpoint = f"{ENDPOINT_BASE}/{user_id}"
    if calendar_id or calendar_events:
        events_endpoint += f"{f'/calendarGroups/{group_id}' if group_id else ''}/calendar{f's/{calendar_id}' if calendar_id else ''}"

    events_endpoint += EVENTS_ENDPOINT + f"/{event_id}"

    return utils.make_delete_request(config.GRAPH_BASE_URI, events_endpoint)


def cancel_user_event(
    event_id, user_id, calendar_events=False, calendar_id=None, group_id=None
):
    events_endpoint = f"{ENDPOINT_BASE}/{user_id}"
    if calendar_id or calendar_events:
        events_endpoint += f"{f'/calendarGroups/{group_id}' if group_id else ''}/calendar{f's/{calendar_id}' if calendar_id else ''}"

    events_endpoint += EVENTS_ENDPOINT + f"/{event_id}/cancel"

    return utils.make_post_request(config.GRAPH_BASE_URI, events_endpoint)

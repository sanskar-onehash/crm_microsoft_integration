from crm_microsoft_integration.microsoft.integration import utils, config

ENDPOINT_BASE = "/users"


def get_user_calendars(user_id, group_id=None):
    return utils.make_get_request(
        config.GRAPH_BASE_URI,
        f"{ENDPOINT_BASE}/{user_id}{'/calendarGroups' if group_id else ''}/calendars",
    )


def get_user_calendar_groups(user_id):
    return utils.make_get_request(
        config.GRAPH_BASE_URI, f"{ENDPOINT_BASE}/{user_id}/calendarGroups"
    )

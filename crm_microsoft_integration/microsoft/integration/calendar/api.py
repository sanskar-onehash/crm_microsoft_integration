from crm_microsoft_integration.microsoft.integration import utils, config

ENDPOINT_BASE = "/users"


def get_user_calendars(user_id):
    return utils.make_get_request(
        config.GRAPH_BASE_URI, f"{ENDPOINT_BASE}/{user_id}/calendars"
    )

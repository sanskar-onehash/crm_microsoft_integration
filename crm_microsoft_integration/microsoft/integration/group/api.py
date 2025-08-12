from crm_microsoft_integration.microsoft.integration import utils, config

ENDPOINT_BASE = "/groups"


def get_groups():
    return utils.make_get_request(config.GRAPH_BASE_URI, ENDPOINT_BASE)


def get_group_members(group_id):
    return utils.make_get_request(
        config.GRAPH_BASE_URI, f"{ENDPOINT_BASE}/{group_id}/members"
    )

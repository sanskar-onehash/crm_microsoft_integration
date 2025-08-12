from crm_microsoft_integration.microsoft.integration import utils, config

ENDPOINT_BASE = "/users"


def get_users():
    return utils.make_get_request(config.GRAPH_BASE_URI, ENDPOINT_BASE)

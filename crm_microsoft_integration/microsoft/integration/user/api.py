from crm_microsoft_integration.microsoft.integration import utils, config

ENDPOINT_BASE = "/users"


def get_users():
    users = []
    next_url = None
    while True:
        users_res = {}
        if not next_url:
            users_res = utils.make_get_request(
                config.GRAPH_BASE_URI, f"{ENDPOINT_BASE}?$orderby=displayName&$top=300"
            )
        else:
            users_res = utils.make_get_request("", "", url=next_url)

        users.extend(users_res["value"])

        if users_res.get("@odata.nextLink"):
            next_url = users_res["@odata.nextLink"]
        else:
            return {**users_res, "value": users}
    return users

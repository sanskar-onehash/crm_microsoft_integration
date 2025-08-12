from crm_microsoft_integration.microsoft.integration.user import api, utils


def get_users():
    users_res = api.get_users()
    return utils.parse_user_res(users_res)

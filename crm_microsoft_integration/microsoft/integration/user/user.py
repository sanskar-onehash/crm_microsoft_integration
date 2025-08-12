from crm_microsoft_integration.microsoft.integration import user


def get_users():
    users_res = user.api.get_users()
    return user.utils.parse_user_response(users_res)

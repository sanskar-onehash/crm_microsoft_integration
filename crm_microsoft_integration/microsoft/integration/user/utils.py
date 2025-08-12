def parse_user_res(users_res):
    parsed_users = []

    for user in users_res["value"]:
        parsed_users.append(
            {
                "display_name": user["displayName"],
                "mail": user["mail"],
                "principal_name": user["userPrincipalName"],
                "id": user["id"],
            }
        )
    return parsed_users

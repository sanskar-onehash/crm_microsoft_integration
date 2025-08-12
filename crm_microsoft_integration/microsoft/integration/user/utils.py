def parse_user_response(users):
    parsed_users = []

    for user in users:
        parsed_users.append(
            {
                "display_name": user["displayName"],
                "mail": user["mail"],
                "principal_name": user["userPrincipalName"],
                "id": user["id"],
            }
        )
    return parsed_users

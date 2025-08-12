def parse_groups_res(groups_res):
    parsed_groups = []

    for group in groups_res["value"]:
        parsed_groups.append(
            {
                "id": group["id"],
                "display_name": group["displayName"],
                "mail": group["mail"],
            }
        )
    return parsed_groups


def parse_group_members_res(members_res, group_id):
    parsed_members = []

    for member in members_res["value"]:
        parsed_members.append(
            {
                "id": member["id"],
                "principal_name": member["userPrincipalName"],
                "display_name": member["displayName"],
                "mail": member["mail"],
                "group": group_id,
            }
        )
    return parsed_members

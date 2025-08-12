from crm_microsoft_integration.microsoft.integration import group


def get_groups(with_users=False):
    group_res = group.api.get_groups()
    groups = group.utils.parse_groups_res(group_res)

    if with_users:
        for group in groups:
            members_res = group.api.get_group_members(group["id"])
            members = group.utils.parse_group_members_res(members_res)

            group["users"] = [{"microsoft_user": member["id"]} for member in members]

    return groups

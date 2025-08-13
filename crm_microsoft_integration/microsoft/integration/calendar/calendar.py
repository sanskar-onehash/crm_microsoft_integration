from crm_microsoft_integration.microsoft.integration.calendar import api, utils


def get_users_calendars(users):
    user_wise_calendars = {}
    for user in users:
        user_wise_calendars[user] = get_user_calendars(user)
    return user_wise_calendars


def get_user_calendars(user):
    calendars_res = api.get_user_calendars(user)
    return utils.parse_calendar_res(calendars_res)


def get_users_calendar_groups(users, with_calendar=False):
    user_wise_calendar_groups = {}
    for user in users:
        user_wise_calendar_groups[user] = get_user_calendar_groups(user, with_calendar)
    return user_wise_calendar_groups


def get_user_calendar_groups(user, with_calendar=False):
    calendar_group_res = api.get_user_calendar_groups(user)
    calendar_groups = utils.parse_calendar_groups_res(calendar_group_res)

    if with_calendar:
        for calendar_group in calendar_groups:
            calendars_res = api.get_user_calendars(user, calendar_group["id"])
            calendar_group["calendars"] = utils.parse_calendar_res(
                calendars_res, calendar_group["id"]
            )

    return calendar_groups

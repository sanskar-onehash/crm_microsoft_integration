from crm_microsoft_integration.microsoft.integration.calendar import api, utils


def get_users_calendars(users):
    user_wise_calendars = {}
    for user in users:
        user_wise_calendars[user] = get_user_calendars(user)
    return user_wise_calendars


def get_user_calendars(user):
    calendars_res = api.get_user_calendars(user)
    return utils.parse_calendar_res(calendars_res)

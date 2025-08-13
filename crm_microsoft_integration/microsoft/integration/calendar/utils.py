def parse_calendar_res(calendar_res, group_id=None):
    parsed_calendars = []

    for calendar in calendar_res["value"]:
        parsed_calendars.append(
            {
                "calendar_name": calendar["name"],
                "change_key": calendar["changeKey"],
                "color": calendar["hexColor"],
                "group_class_id": calendar["groupClassId"],
                "id": calendar["id"],
                "is_default_calendar": calendar["isDefaultCalendar"],
                "owner_email": calendar["owner"]["address"],
                "owner_name": calendar["owner"]["name"],
                "calendar_group": group_id,
            }
        )

    return parsed_calendars


def parse_calendar_groups_res(calendar_group_res):
    parsed_calendar_groups = []

    for calendar_group in calendar_group_res["value"]:
        parsed_calendar_groups.append(
            {
                "id": calendar_group["id"],
                "group_name": calendar_group["name"],
                "class_id": calendar_group["classId"],
                "change_key": calendar_group["changeKey"],
            }
        )
    return parsed_calendar_groups

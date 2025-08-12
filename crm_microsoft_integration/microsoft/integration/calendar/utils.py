def parse_calendar_res(calendar_res):
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
            }
        )

    return parsed_calendars

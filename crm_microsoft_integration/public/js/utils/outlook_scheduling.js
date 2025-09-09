frappe.provide("microsoft.utils");
frappe.provide("microsoft.utils.outlook_scheduling");

const DEFAULT_PROPOSAL_COLOR = "orange";
const DEFAULT_HOLIDAY_COLOR = "red";

$.extend(microsoft.utils.outlook_scheduling, {
  schedule_new_event(frm, scheduled_events_wrapper, default_data = {}) {
    return new microsoft.utils.OutlookScheduling({
      frm,
      scheduled_events_wrapper,
      default_data,
    });
  },
});

microsoft.utils.OutlookScheduling = class OutlookScheduling {
  constructor(opts) {
    const defaults = {
      set_email_template_subject: true,
      force_email_template_subject: false,
    };
    $.extend(this, defaults, opts);

    this.form_wrapper = $(this.frm.wrapper);
    this.setup();
  }

  async setup() {
    // Set current microsoft user
    this.cur_microsoft_user =
      (
        await frappe.db.get_value(
          "Microsoft User",
          { user: frappe.session.user },
          "name",
        )
      ).message?.name || "";

    if (this.cur_microsoft_user) {
      // Set default calendar for the user
      this.cur_user_default_calendar =
        (
          await frappe.db.get_value(
            "Outlook Calendar",
            {
              microsoft_user: this.cur_microsoft_user,
              is_default_calendar: true,
            },
            "name",
          )
        ).message?.name || "";
    }
  }

  refresh() {
    var me = this;
    $(this.scheduled_events_wrapper).empty();
    // let cur_form_footer = this.form_wrapper.find(".form-footer");

    // if (!$(this.all_activities_wrapper).find(".form-footer").length) {
    //   this.all_activities_wrapper.empty();
    //   $(cur_form_footer).appendTo(this.all_activities_wrapper);
    //
    //   // remove frappe-control class to avoid absolute position for action-btn
    //   $(this.all_activities_wrapper).removeClass("frappe-control");
    // }

    frappe.call({
      method: "crm_microsoft_integration.microsoft.utils.get_reference_events",
      args: {
        ref_doctype: this.frm.doc.doctype,
        ref_docname: this.frm.doc.name,
        with_slots: true,
      },
      callback: (r) => {
        if (!r.exc) {
          me.events_data = r.message;
          const activities_html = frappe.render_template("outlook_scheduling", {
            events: r.message.events,
          });

          $(activities_html).appendTo(me.scheduled_events_wrapper);
          me.format_dates();
          me.setup_listeners();
          me.on_refresh && me.on_refresh();
        }
      },
    });
  }

  setup_listeners() {
    this.scheduled_events_wrapper
      .off("click")
      .on("click", this.wrapper_click_handler());
  }

  wrapper_click_handler() {
    const me = this;
    return function (e) {
      const closest_schedule_btn = e.target.closest(".schedule-btn");
      const closest_reschedule_btn = e.target.closest(".reschedule-btn");
      const closest_cancel_btn = e.target.closest(".cancel-btn");
      const closest_edit_btn = e.target.closest(".edit-btn");

      if (closest_schedule_btn) {
        me.handle_schedule_event(e, closest_schedule_btn);
      } else if (closest_reschedule_btn) {
        me.handle_reschedule_event(
          e,
          closest_reschedule_btn,
          +closest_reschedule_btn.dataset.eventIdx,
        );
      } else if (closest_cancel_btn) {
        me.handle_event_cancel(
          e,
          closest_cancel_btn,
          +closest_cancel_btn.dataset.eventIdx,
        );
      } else if (closest_edit_btn) {
        me.handle_event_edit(
          e,
          closest_edit_btn,
          +closest_edit_btn.dataset.eventIdx,
        );
      }
    };
  }

  format_dates() {
    $(this.scheduled_events_wrapper)
      .find("[data-format-date]")
      .each((_, el) => {
        el.textContent = this.format_date(el.getAttribute("data-format-date"));
      });
  }

  async handle_event_edit(e, e_src, event_idx) {
    e_src.disabled = true;
    this.current_dialog = await this.get_edit_dialog(event_idx);
    this.current_dialog.event_src_el = e_src;
    this.current_dialog.show();
  }

  async handle_event_cancel(e, e_src, event_idx) {
    e_src.disabled = true;
    this.current_dialog = this.get_cancel_dialog(event_idx);
    this.current_dialog.event_src_el = e_src;
    this.current_dialog.show();
  }

  handle_reschedule_event(e, e_src, event_idx) {
    e_src.disabled = true;
    this.load_lib().then(async () => {
      this.current_dialog = await this.get_reschedule_dialog(event_idx);
      this.current_dialog.event_src_el = e_src;
      this.current_dialog.show();
    });
  }

  handle_schedule_event(e, e_src) {
    e_src.disabled = true;
    this.load_lib().then(async () => {
      this.current_dialog = await this.get_slot_dialog(this.default_data);
      this.current_dialog.event_src_el = e_src;
      this.current_dialog.show();
    });
  }

  add_slot_handler() {
    const me = this;
    return function () {
      me.calendar_dialog = me.get_calendar_dialog();
      me.calendar = new frappe.views.Calendar(
        me.get_calendar_preferences(
          me.calendar_dialog.fields_dict.calendar_html.$wrapper,
        ),
      );
      me.calendar_dialog.show();
    };
  }

  handle_group_change() {
    let me = this;
    const group_value = me.current_dialog.get_value("user_group");
    if (group_value) {
      frappe.db
        .get_list("User Group Member", {
          parent_doctype: "User Group",
          filters: { parent: group_value },
          fields: ["user"],
        })
        .then((group_members) => {
          const updated_value = me.current_dialog.get_value("users");
          const old_users = updated_value.map((user) => user.user);

          for (let group_user of group_members) {
            if (!old_users.includes(group_user.user)) {
              updated_value.push({ user: group_user.user });
            }
          }
          me.current_dialog.set_value("users", updated_value);
          me.current_dialog.set_value("user_group", "");
        });
    }
  }

  edit_event_handler(event) {
    const me = this;
    return function (values) {
      const editingMsg = frappe.msgprint("Editing event...");
      frappe.call({
        method:
          "crm_microsoft_integration.microsoft.doctype.outlook_event_slot.outlook_event_slot.edit_event",
        args: {
          event_type: event.type,
          event_name: event.name,
          subject: values.subject || "",
          description: values.description || "",
          add_teams_meet: values.add_teams_meet || false,
          event_location: values.event_location || "",
          event_participants: values.event_participants || [],
          users: values.users || [],
        },
        callback: function (res) {
          if (!res.exc) {
            me.current_dialog.event_src_el.disabled = false;
            me.current_dialog.hide();
            me.refresh();
            editingMsg.hide();
            frappe.show_alert({
              message: "Event Edited successfully",
              indicator: "green",
            });
          }
        },
      });
    };
  }

  event_cancel_handler(event_idx) {
    const me = this;
    const event = me.events_data.events[event_idx];
    return function (values) {
      const cancellingMsg = frappe.msgprint("Cancelling event...");
      frappe.call({
        method:
          "crm_microsoft_integration.microsoft.doctype.outlook_event_slot.outlook_event_slot.cancel_event",
        args: {
          event_type: event.type,
          event_name: event.name,
          cancel_reason: values.cancel_reason,
        },
        callback: function (res) {
          if (!res.exc) {
            me.current_dialog.event_src_el.disabled = false;
            me.current_dialog.hide();
            me.refresh();
            cancellingMsg.hide();
            frappe.show_alert({
              message: "Event Cancelled successfully",
              indicator: "green",
            });
          }
        },
      });
    };
  }

  reschedule_slot_handler(event_idx) {
    const me = this;
    const event = me.events_data.events[event_idx];
    return function (values) {
      const reschedulingMsg = frappe.msgprint("Rescheduling Event Slots...");
      frappe.call({
        method:
          "crm_microsoft_integration.microsoft.doctype.outlook_event_slot.outlook_event_slot.reschedule_event_slots",
        args: {
          event_type: event.type,
          event_name: event.name,
          new_slots: values.slot_proposals,
          reschedule_reason: values.reschedule_reason,
        },
        callback: function (res) {
          if (!res.exc) {
            me.current_dialog.event_src_el.disabled = false;
            me.current_dialog.hide();
            me.refresh();
            reschedulingMsg.hide();
            frappe.show_alert({
              message: "Event slots rescheduled successfully.",
              indicator: "green",
            });
          }
        },
      });
    };
  }

  schedule_slot_handler() {
    const me = this;
    return function (values) {
      const creatingMsg = frappe.msgprint("Creating Event Slots...");
      frappe.call({
        method:
          "crm_microsoft_integration.microsoft.doctype.outlook_event_slot.outlook_event_slot.create_slot",
        args: {
          doc: values,
        },
        callback: function (res) {
          if (!res.exc) {
            me.current_dialog.event_src_el.disabled = false;
            me.current_dialog.hide();
            me.refresh();
            creatingMsg.hide();
            frappe.show_alert({
              message: "Event slots created successfully.",
              indicator: "green",
            });
          }
        },
      });
    };
  }

  handle_dialog_cancel_event() {
    return () => {
      this.current_dialog.event_src_el.disabled = false;
    };
  }

  async update_status(input_field, doctype) {
    let completed = $(input_field).prop("checked") ? 1 : 0;
    let docname = $(input_field).attr("name");
    if (completed) {
      await frappe.db.set_value(doctype, docname, "status", "Closed");
      this.refresh();
    }
  }

  handle_slot_email_template() {
    if (!this.set_email_template_subject) {
      return;
    }
    if (
      this.current_dialog.get_value("subject") &&
      !this.force_email_template_subject
    ) {
      return;
    }

    const email_template = this.current_dialog.get_value("email_template");
    if (!email_template) {
      return;
    }

    frappe.db
      .get_value("Email Template", email_template, "subject")
      .then((subject_res) => {
        if (subject_res.message?.subject) {
          this.current_dialog.set_value("subject", subject_res.message.subject);
        }
      });
  }

  async get_edit_dialog(event_idx) {
    const event = this.events_data.events[event_idx];
    const BTN_LABEL = "Edit Event";
    const fields = [
      {
        fieldname: "subject",
        fieldtype: "Small Text",
        label: "Subject",
        reqd: 1,
        default: event.subject,
      },
      {
        fieldname: "description",
        fieldtype: "Text Editor",
        label: "Description",
        default: event.description,
      },
      {
        fieldtype: "Column Break",
        fieldname: "culumn_break_1",
      },
      {
        fieldname: "add_teams_meet",
        fieldtype: "Check",
        label: "Add Teams Meet",
        default: event.is_online,
      },
      {
        fieldname: "event_location",
        fieldtype: "Small Text",
        label: "Event Location",
        default: event.location,
      },
      {
        fieldname: "user_group",
        fieldtype: "Link",
        label: "User Group",
        options: "User Group",
        onchange: () => this.handle_group_change(),
      },
      {
        fieldname: "users",
        fieldtype: "Table MultiSelect",
        label: "Users",
        options: "User Group Member",
        default: event.participants
          .filter((participant) => participant.ref_doctype === "User")
          .map((participant) => ({ user: participant.ref_docname })),
      },
      {
        fieldname: "section_break_3",
        fieldtype: "Section Break",
      },
      {
        fieldname: "event_participants",
        fieldtype: "Table",
        label: "Event Participants",
        options: "Event Participants",
        fields: this.prepare_table_fields(
          await this.get_docfields("Event Participants"),
        ),
        reqd: 1,
        data: event.participants
          .filter((participant) => participant.ref_doctype !== "User")
          .map((participant) => {
            return {
              reference_doctype: participant.ref_doctype,
              reference_docname: participant.ref_docname,
              email: participant.email,
              custom_participant_name: participant.participant_name,
              custom_required: participant.is_required,
            };
          }),
      },
    ];
    return new frappe.ui.Dialog({
      title: "Edit Event",
      fields,
      size: "large", // small, large, extra-large
      primary_action_label: BTN_LABEL,
      primary_action: this.edit_event_handler(event),
      on_hide: this.handle_dialog_cancel_event(),
    });
  }

  get_cancel_dialog(event_idx) {
    const BTN_LABEL = "Cancel Event";
    const fields = [
      {
        fieldname: "cancel_reason",
        fieldtype: "Small Text",
        label: "Cancel Reason",
        reqd: 1,
      },
    ];
    return new frappe.ui.Dialog({
      title: "Cancel Event",
      fields,
      size: "small", // small, large, extra-large
      primary_action_label: BTN_LABEL,
      primary_action: this.event_cancel_handler(event_idx),
      on_hide: this.handle_dialog_cancel_event(),
    });
  }

  async get_reschedule_dialog(event_idx) {
    const BTN_LABEL = "Reschedule Event";
    const fields = [
      {
        fieldname: "slot_proposals",
        fieldtype: "Table",
        label: "Slot Proposals",
        options: "Outlook Slot Proposals",
        fields: this.prepare_table_fields(
          await this.get_docfields("Outlook Slot Proposals"),
        ),
        reqd: 1,
        cannot_add_rows: 1,
      },
      {
        fieldname: "add_slot",
        fieldtype: "Button",
        label: "Add Slot",
        click: this.add_slot_handler(),
      },
      {
        fieldname: "reschedule_reason",
        fieldtype: "Small Text",
        label: "Reschedule Reason",
        reqd: 1,
      },
    ];
    return new frappe.ui.Dialog({
      title: "Reschedule Event",
      fields,
      size: "large", // small, large, extra-large
      primary_action_label: BTN_LABEL,
      primary_action: this.reschedule_slot_handler(event_idx),
      on_hide: this.handle_dialog_cancel_event(),
    });
  }

  async get_slot_dialog(default_data) {
    const BTN_LABEL = "Schedule Event";
    const fields = [
      {
        label: "Email Template",
        fieldtype: "Link",
        fieldname: "email_template",
        options: "Email Template",
        change: () => this.handle_slot_email_template(),
      },
      {
        label: "Subject",
        fieldtype: "Small Text",
        fieldname: "subject",
        fetch_from: "email_template.subject",
        fetch_if_empty: 1,
        reqd: 1,
      },
      {
        fieldname: "description",
        fieldtype: "Text Editor",
        label: "Description",
      },
      {
        fieldtype: "Column Break",
        fieldname: "culumn_break_1",
      },
      {
        label: "Outlook Calendar",
        fieldtype: "Link",
        fieldname: "outlook_calendar",
        options: "Outlook Calendar",
        default: this.cur_user_default_calendar,
        reqd: 1,
      },
      {
        label: "Organiser",
        fieldtype: "Link",
        fieldname: "organiser",
        options: "Microsoft User",
        reqd: 1,
        default: this.cur_microsoft_user,
      },
      {
        default: "1",
        fieldname: "add_teams_meet",
        fieldtype: "Check",
        label: "Add Teams Meet",
      },
      {
        fieldname: "event_location",
        fieldtype: "Small Text",
        label: "Event Location",
      },
      {
        default: "0",
        fieldname: "all_day",
        fieldtype: "Check",
        label: "All Day",
        hidden: 1,
      },
      {
        default: "0",
        fieldname: "repeat_this_event",
        fieldtype: "Check",
        label: "Repeat this Event",
        hidden: 1,
      },
      {
        fieldname: "section_break_1",
        fieldtype: "Section Break",
      },
      {
        fieldname: "slot_proposals",
        fieldtype: "Table",
        label: "Slot Proposals",
        options: "Outlook Slot Proposals",
        fields: this.prepare_table_fields(
          await this.get_docfields("Outlook Slot Proposals"),
        ),
        reqd: 1,
        cannot_add_rows: 1,
      },
      {
        fieldname: "add_slot",
        fieldtype: "Button",
        label: "Add Slot",
        click: this.add_slot_handler(),
      },
      {
        fieldname: "column_break_2",
        fieldtype: "Column Break",
      },
      {
        fieldname: "user_group",
        fieldtype: "Link",
        label: "User Group",
        options: "User Group",
        onchange: () => this.handle_group_change(),
      },
      {
        fieldname: "users",
        fieldtype: "Table MultiSelect",
        label: "Users",
        options: "User Group Member",
      },
      {
        fieldname: "section_break_3",
        fieldtype: "Section Break",
      },
      {
        fieldname: "event_participants",
        fieldtype: "Table",
        label: "Event Participants",
        options: "Event Participants",
        fields: this.prepare_table_fields(
          await this.get_docfields("Event Participants"),
        ),
        reqd: 1,
      },
      {
        fieldtype: "Section Break",
        fieldname: "section_break_4",
      },
      {
        depends_on: "repeat_this_event",
        fieldname: "repeat_on",
        fieldtype: "Select",
        label: "Repeat On",
        options: "\nDaily\nWeekly\nMonthly\nYearly",
      },
      {
        depends_on: "repeat_this_event",
        description: "Leave blank to repeat always",
        fieldname: "repeat_till",
        fieldtype: "Date",
        label: "Repeat Till",
      },
      {
        fieldtype: "Column Break",
        fieldname: "column_break_3",
      },
      {
        default: "0",
        depends_on: 'eval: doc.repeat_this_event && doc.repeat_on==="Weekly"',
        fieldname: "monday",
        fieldtype: "Check",
        label: "Monday",
      },
      {
        default: "0",
        depends_on: 'eval: doc.repeat_this_event && doc.repeat_on==="Weekly"',
        fieldname: "tuesday",
        fieldtype: "Check",
        label: "Tuesday",
      },
      {
        default: "0",
        depends_on: 'eval: doc.repeat_this_event && doc.repeat_on==="Weekly"',
        fieldname: "wednesday",
        fieldtype: "Check",
        label: "Wednesday",
      },
      {
        default: "0",
        depends_on: 'eval: doc.repeat_this_event && doc.repeat_on==="Weekly"',
        fieldname: "thursday",
        fieldtype: "Check",
        label: "Thursday",
      },
      {
        default: "0",
        depends_on: 'eval: doc.repeat_this_event && doc.repeat_on==="Weekly"',
        fieldname: "friday",
        fieldtype: "Check",
        label: "Friday",
      },
      {
        default: "0",
        depends_on: 'eval: doc.repeat_this_event && doc.repeat_on==="Weekly"',
        fieldname: "saturday",
        fieldtype: "Check",
        label: "Saturday",
      },
      {
        default: "0",
        depends_on: 'eval: doc.repeat_this_event && doc.repeat_on==="Weekly"',
        fieldname: "sunday",
        fieldtype: "Check",
        label: "Sunday",
      },
    ];
    for (let field of fields) {
      if (default_data[field.fieldname]) {
        if (field.fieldtype === "Table") {
          field.data = default_data[field.fieldname];
        } else {
          field.default = default_data[field.fieldname];
        }
      }
    }
    return new frappe.ui.Dialog({
      title: "Schedule Event",
      fields,
      size: "extra-large", // small, large, extra-large
      primary_action_label: BTN_LABEL,
      primary_action: this.schedule_slot_handler(),
      on_hide: this.handle_dialog_cancel_event(),
    });
  }

  get_calendar_dialog() {
    return new frappe.ui.Dialog({
      title: "Calendar",
      fields: [
        {
          fieldtype: "HTML",
          fieldname: "calendar_html",
        },
      ],
      size: "large", // small, large, extra-large
    });
  }

  calendar_event_after_all_render() {
    if (this.calendar.render_all_triggerd) {
      return;
    }
    this.calendar.render_all_triggerd = true;
    (this.current_dialog.get_value("slot_proposals") || []).forEach(
      (proposal) => {
        this.calendar.$cal.fullCalendar("renderEvent", {
          start: proposal.starts_on,
          end: proposal.ends_on,
          title: this.current_dialog.get_value("subject"),
          backgroundColor: frappe.ui.color.get(
            DEFAULT_PROPOSAL_COLOR,
            "extra-light",
          ),
          textColor: frappe.ui.color.get(DEFAULT_PROPOSAL_COLOR, "dark"),
        });
      },
    );
  }

  get_calendar_preferences(parent) {
    return {
      scheduling: this,
      options: {
        editable: false,
        eventStartEditable: false,
        eventDurationEditable: false,
        selectable: true,
        events: (start, end, timezone, callback) =>
          this.calendar_get_events(start, end, timezone, callback),
        eventAfterAllRender: () => this.calendar_event_after_all_render(),
        select: (startDate, endDate, jsEvent, view) =>
          this.calendar_event_slot_select(startDate, endDate, jsEvent, view),
        eventClick: () => {},
        eventDrop: () => {},
        eventResize: () => {},
      },
      doctype: "Event",
      field_map: {
        id: "name",
        start: "starts_on",
        end: "ends_on",
        title: "subject",
        allDay: 0,
      },
      parent,
      page: this.frm.page,
      // Mock list_view
      list_view: {
        filter_area: {
          get() {
            return [];
          },
        },
      },
    };
  }

  calendar_get_events(start, end, timezone, callback) {
    const events_promise = frappe.call({
      method:
        this.calendar.get_events_method || "frappe.desk.calendar.get_events",
      type: "GET",
      args: this.calendar.get_args(start, end),
    });
    const holidays_promise = frappe.db.get_list("Holiday List", {
      filters: { from_date: [">=", start], to_date: ["<=", end] },
      fields: ["holiday_list_name", "color", "name", "from_date", "to_date"],
      limit: 500,
    });

    return Promise.all([events_promise, holidays_promise]).then(
      (promise_res) => {
        const events_res = promise_res[0];
        const holidays_res = promise_res[1];

        const events = this.calendar.prepare_events(events_res.message || []);
        const holidays = this.prepare_holidays(holidays_res);

        callback([...events, ...holidays]);
      },
    );
  }

  prepare_holidays(holidays_res) {
    return (holidays_res || []).map((d) => {
      d.id = d.name;
      d.editable = frappe.model.can_write("Holiday List");
      d.start = d.from_date;
      d.end = d.to_date;

      // show event on single day if start or end date is invalid
      if (!frappe.datetime.validate(d.start) && d.end) {
        d.start = frappe.datetime.add_days(d.end, -1);
      }

      if (d.start && !frappe.datetime.validate(d.end)) {
        d.end = frappe.datetime.add_days(d.start, 1);
      }

      this.calendar.fix_end_date_for_event_render(d);

      d.title = frappe.utils.html2text(d.holiday_list_name);
      d.rendering = "background";
      d.backgroundColor = frappe.ui.color.get(DEFAULT_HOLIDAY_COLOR, "default");

      return d;
    });
  }

  calendar_event_slot_select(startDate, endDate, jsEvent, view) {
    if (view.name === "month" && endDate - startDate === 86400000) {
      // detect single day click in month view
      return;
    }

    const proposals_grid = this.current_dialog.fields_dict.slot_proposals.grid;
    if (proposals_grid) {
      if (!proposals_grid.df.data) {
        proposals_grid.df.data = proposals_grid.get_data() || [];
      }
      const row_idx = proposals_grid.df.data.length + 1;
      proposals_grid.df.data.push({
        idx: row_idx,
        __islocal: true,
        starts_on: frappe.datetime.get_datetime_as_string(startDate, false),
        ends_on: frappe.datetime.get_datetime_as_string(endDate, false),
      });
      proposals_grid.df.on_add_row && proposals_grid.df.on_add_row(row_idx);
      proposals_grid.refresh();

      this.calendar_dialog.cancel();
    }
  }

  load_lib() {
    return new Promise((resolve) => {
      if (this.required_libs) {
        frappe.require(this.required_libs, resolve);
      } else {
        resolve();
      }
    });
  }

  prepare_table_fields(fields) {
    return fields.map((field) => {
      if (field.fieldtype === "Dynamic Link") {
        field.get_options = this.handle_dialog_table_dynamic_field_options;
      }
      return field;
    });
  }

  handle_dialog_table_dynamic_field_options(dynamic_field_control) {
    return dynamic_field_control.doc[dynamic_field_control.df.options];
  }

  get_docfields(doctype) {
    return new Promise((resolve) => {
      const docfields = frappe.meta.get_docfields(doctype);
      if (docfields && docfields.length) {
        return resolve(docfields);
      }

      frappe.model.with_doctype(doctype, () => {
        return resolve(frappe.meta.get_docfields(doctype));
      });
    });
  }

  get calendar_name() {
    return "Event";
  }

  get required_libs() {
    let assets = [
      "assets/frappe/js/lib/fullcalendar/fullcalendar.min.css",
      "assets/frappe/js/lib/fullcalendar/fullcalendar.min.js",
    ];
    let user_language = frappe.boot.lang;
    if (user_language && user_language !== "en") {
      assets.push("assets/frappe/js/lib/fullcalendar/locale-all.js");
    }
    return assets;
  }

  format_date(inputStr) {
    const cleanedInput = inputStr.split(".")[0];

    const isoStr = cleanedInput.replace(" ", "T");

    const date = new Date(isoStr);

    // Convert to IST (+5:30)
    const options = {
      timeZone: "Asia/Kolkata",
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    };

    const formatter = new Intl.DateTimeFormat("en-IN", options);
    return formatter.format(date);
  }
};

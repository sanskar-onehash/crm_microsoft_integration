frappe.listview_settings["Outlook Calendar"] = {
  onload: function (listview) {
    addOutlookCalendarListActions(listview);
  },
};

function addOutlookCalendarListActions(listview) {
  addSyncOutlookCalendarBtn(listview);
}

function addSyncOutlookCalendarBtn(listview) {
  const DIALOG_TITLE = "Syncing Outlook Calendars";

  listview.page.add_inner_button("Sync Outlook Calendars", function () {
    frappe.call({
      method:
        "crm_microsoft_integration.microsoft.doctype.outlook_calendar.outlook_calendar.sync_outlook_calendars",
      callback: function (response) {
        if (response && response.message) {
          if (response.message.status === "success") {
            frappe.show_alert(
              response.message.msg || "Outlook Calendar syncing started.",
              5,
            );

            function handleRealtimeProgress(msg) {
              progressDialog = frappe.show_progress(
                msg.title || DIALOG_TITLE,
                msg.progress,
                msg.total,
                "Please Wait...",
                true,
              );

              if (msg.progress === msg.total) {
                frappe.show_alert(
                  {
                    indicator: "green",
                    message: "Outlook Calendar synced successfully.",
                  },
                  5,
                );
                frappe.realtime.off(
                  response.message.track_on,
                  handleRealtimeProgress,
                );
              }
            }
            frappe.realtime.on(
              response.message.track_on,
              handleRealtimeProgress,
            );
          } else {
            frappe.throw(
              `Error occured during syncing calendars: ${response.message}`,
            );
          }
        }
      },
    });
  });
}

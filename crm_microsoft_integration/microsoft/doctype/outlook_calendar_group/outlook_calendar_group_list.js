frappe.listview_settings["Outlook Calendar Group"] = {
  onload: function (listview) {
    addOutlookCalGroupListActions(listview);
  },
};

function addOutlookCalGroupListActions(listview) {
  addSyncOutlookCalGroupBtn(listview);
}

function addSyncOutlookCalGroupBtn(listview) {
  const DIALOG_TITLE = "Syncing Outlook Calendar Groups";

  listview.page.add_inner_button("Sync Outlook Calendar Groups", function () {
    frappe.call({
      method:
        "crm_microsoft_integration.microsoft.doctype.outlook_calendar_group.outlook_calendar_group.sync_outlook_calendar_groups",
      callback: function (response) {
        if (response && response.message) {
          if (response.message.status === "success") {
            frappe.show_alert(
              response.message.msg ||
                "Outlook Calendar Groups syncing started.",
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
                    message: "Outlook Calendar Groups synced successfully.",
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
              `Error occured during syncing outlook calendar groups: ${response.message}`,
            );
          }
        }
      },
    });
  });
}

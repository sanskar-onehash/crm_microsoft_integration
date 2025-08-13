frappe.listview_settings["Event"] = {
  onload: function (listview) {
    addOutlookEventListActions(listview);
  },
};

function addOutlookEventListActions(listview) {
  addSyncOutlookEventsBtn(listview);
}

function addSyncOutlookEventsBtn(listview) {
  const DIALOG_TITLE = "Syncing Outlook Events";

  listview.page.add_inner_button("Sync Outlook Events", function () {
    frappe.call({
      method:
        "crm_microsoft_integration.microsoft.customizations.event.sync_outlook_events",
      callback: function (response) {
        if (response && response.message) {
          if (response.message.status === "success") {
            frappe.show_alert(
              response.message.msg || "Outlook Event syncing started.",
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
                    message: "Outlook Event synced successfully.",
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
              `Error occured during syncing events: ${response.message}`,
            );
          }
        }
      },
    });
  });
}

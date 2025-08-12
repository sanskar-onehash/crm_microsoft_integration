frappe.listview_settings["Microsoft User"] = {
  onload: function (listview) {
    addMSListActions(listview);
  },
};

function addMSListActions(listview) {
  addSyncMSUserBtn(listview);
}

function addSyncMSUserBtn(listview) {
  const DIALOG_TITLE = "Syncing Microsoft Users";

  listview.page.add_inner_button("Sync Microsoft Users", function () {
    frappe.call({
      method:
        "crm_microsoft_integration.microsoft.doctype.microsoft_user.microsoft_user.sync_ms_users",
      callback: function (response) {
        if (response && response.message) {
          if (response.message.status === "success") {
            frappe.show_alert(
              response.message.msg || "Microsoft Users syncing started.",
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
                    message: "Microsoft Users synced successfully.",
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
              `Error occured during syncing users: ${response.message}`,
            );
          }
        }
      },
    });
  });
}

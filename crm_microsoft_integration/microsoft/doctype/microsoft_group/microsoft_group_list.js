frappe.listview_settings["Microsoft Group"] = {
  onload: function (listview) {
    addMSGroupListActions(listview);
  },
};

function addMSGroupListActions(listview) {
  addSyncMSGroupBtn(listview);
}

function addSyncMSGroupBtn(listview) {
  const DIALOG_TITLE = "Syncing Microsoft Groups";

  listview.page.add_inner_button("Sync Microsoft Groups", function () {
    frappe.call({
      method:
        "crm_microsoft_integration.microsoft.doctype.microsoft_group.microsoft_group.sync_ms_groups",
      callback: function (response) {
        if (response && response.message) {
          if (response.message.status === "success") {
            frappe.show_alert(
              response.message.msg || "Microsoft Groups syncing started.",
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
                    message: "Microsoft Groups synced successfully.",
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
              `Error occured during syncing groups: ${response.message}`,
            );
          }
        }
      },
    });
  });
}

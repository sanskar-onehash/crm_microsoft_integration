// Copyright (c) 2025, OneHash and contributors
// For license information, please see license.txt

frappe.ui.form.on("Microsoft Settings", {
  async provide_consent(frm) {
    if (frm.is_dirty()) {
      frappe.msgprint("Please save the form first.");
      return;
    }

    const consentUri = await getConsentUri();
    if (consentUri) {
      redirectToUri(consentUri);
    }
  },
});

function getConsentUri() {
  return new Promise((resolve, reject) => {
    frappe.call({
      method:
        "crm_microsoft_integration.microsoft.doctype.microsoft_settings.microsoft_settings.get_consent_uri",
      callback: function (data) {
        resolve(data.message);
      },
      error: () => reject("Error occured while requesting consent uri."),
      always: () => resolve(),
      freeze: true,
      freeze_message: "Requesting consent uri.",
    });
  });
}

function redirectToUri(uri) {
  window.location.href = uri;
}

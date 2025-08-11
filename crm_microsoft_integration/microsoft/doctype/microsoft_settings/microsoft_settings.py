# Copyright (c) 2025, OneHash and contributors
# For license information, please see license.txt

import frappe
from frappe import utils as f_utils
from frappe.model.document import Document
from crm_microsoft_integration.microsoft.integration import utils


class MicrosoftSettings(Document):

    @property
    def redirect_uri(self):
        return utils.get_redirect_uri()


def get_mi_settings(raise_exception=True):
    mi_settings = frappe.get_single("Microsoft Settings")
    if not mi_settings.enabled:
        frappe.throw("Microsoft Settings is not enabled.")

    return mi_settings


@frappe.whitelist()
def get_consent_uri():
    mi_settings = get_mi_settings()

    consent_hash = frappe.generate_hash(length=64)
    mi_settings.set("consent_hash", consent_hash)
    mi_settings.save()

    consent_url = utils.get_consent_uri(
        mi_settings.client_id, consent_hash, mi_settings.tenant_id
    )

    if frappe.request.method == "GET":
        frappe.db.commit()

    return consent_url


def verify_consent_permit(tenant, consent_id, admin_consent):
    mi_settings = get_mi_settings()

    if not admin_consent:
        frappe.throw("Admin consent cancelled.")

    if consent_id != mi_settings.consent_hash:
        frappe.throw("Consent hash didn't matched. Invalid Request Flow.")

    if not mi_settings.tenant_id:
        mi_settings.set("tenant_id", tenant)
        mi_settings.save()
        if frappe.request.method == "GET":
            frappe.db.commit()

    elif mi_settings.tenant_id != tenant:
        frappe.throw("Tenant ID didn't matched. Can't provide access.")

    return True


def get_access_token():
    mi_settings = get_mi_settings()

    if (
        not mi_settings.access_token_expiry
        or mi_settings.access_token_expiry <= f_utils.get_datetime()
    ):
        return None

    return f"{mi_settings.token_type} {mi_settings.get_password('access_token')}"


def set_access_token(token_type, access_token, expires_in):
    access_token_expiry = f_utils.add_to_date(
        f_utils.get_datetime(),
        seconds=expires_in - 300,  # 300s/5m as a safety buffer
    )

    mi_settings = get_mi_settings()
    mi_settings.update(
        {
            "token_type": token_type,
            "access_token": access_token,
            "access_token_expiry": access_token_expiry,
        }
    )
    mi_settings.save()
    frappe.db.commit()


def get_client_credentials():
    mi_settings = get_mi_settings()
    return {
        "client_id": mi_settings.client_id,
        "client_secret": mi_settings.get_password("client_secret_value"),
    }

import frappe

from frappe.utils import get_url_to_list
from crm_microsoft_integration.microsoft.integration import utils, config, service


@frappe.whitelist(allow_guest=True)
def permit(tenant, state, admin_consent):
    service.verify_consent_permit(tenant, state, admin_consent)
    get_access_token(generate=True)

    frappe.db.commit()
    frappe.response["type"] = "redirect"
    frappe.response["location"] = get_url_to_list("Microsoft Settings")


def get_access_token(generate=False):
    if not generate:
        access_token = service.get_last_access_token()
        if access_token:
            return access_token

    client_credentials = service.get_client_credentials()
    payload = {
        "client_id": client_credentials["client_id"],
        "client_secret": client_credentials["client_secret"],
        "grant_type": config.MI_AUTH_GRANT_TYPE,
        "scope": config.MI_AUTH_SCOPE,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = utils.make_post_request(
        config.MI_BASE_URI,
        f"/{client_credentials['tenant_id']}{config.MI_ACESS_TOKEN_ENDPOINT}",
        auth=False,
        data=payload,
        headers=headers,
    )
    service.set_access_token(
        data["token_type"], data["access_token"], data["expires_in"]
    )

    return f"{data['token_type']} {data['access_token']}"

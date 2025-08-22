import frappe
import requests

from frappe import utils
from crm_microsoft_integration.microsoft.integration import config, auth


def get_auth_headers():
    return {"Authorization": auth.get_access_token()}


def prepare_headers(headers=None, auth=True):
    if not headers:
        headers = {"Content-Type": "application/json"}
    if auth:
        headers.update(get_auth_headers())
    return headers


def make_get_request(
    base_uri, endpoint, auth=True, params=None, headers=None, url=None
):
    headers = prepare_headers(headers, auth)

    res = requests.get(
        f"{url if url else base_uri + endpoint}", params=params, headers=headers
    )
    res.raise_for_status()

    if res.text:
        return res.json()


def make_post_request(
    base_uri, endpoint, auth=True, headers=None, params=None, data=None, json=None
):
    headers = prepare_headers(headers, auth)

    res = requests.post(
        f"{base_uri}{endpoint}",
        headers=headers,
        params=params,
        data=data,
        json=json,
    )
    res.raise_for_status()

    if res.text:
        return res.json()


def make_patch_request(
    base_uri, endpoint, auth=True, headers=None, params=None, data=None, json=None
):
    headers = prepare_headers(headers, auth)

    res = requests.patch(
        f"{base_uri}{endpoint}",
        headers=headers,
        params=params,
        data=data,
        json=json,
    )
    res.raise_for_status()

    if res.text:
        return res.json()


def make_delete_request(
    base_uri, endpoint, auth=True, headers=None, params=None, data=None, json=None
):
    headers = prepare_headers(headers, auth)

    res = requests.delete(
        f"{base_uri}{endpoint}",
        headers=headers,
        params=params,
        data=data,
        json=json,
    )
    res.raise_for_status()

    if res.text:
        return res


def get_redirect_uri():
    return f"{utils.get_url()}{config.APP_REDIRECT_ENDPOINT}"


def get_consent_uri(client_id, state, tenant_id=None):
    if not client_id:
        frappe.throw("Client Id is required.")
    if not state:
        frappe.throw("State is required")
    if not tenant_id:
        tenant_id = "common"

    params = utils.urlencode(
        {"client_id": client_id, "state": state, "redirect_uri": get_redirect_uri()}
    )

    return (
        f"{config.MI_BASE_URI}/{tenant_id}{config.MI_ADMIN_CONSENT_ENDPOINT}?{params}"
    )

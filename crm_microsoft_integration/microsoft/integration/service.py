from crm_microsoft_integration.microsoft.doctype.microsoft_settings import (
    microsoft_settings as mi_settings,
)


def verify_consent_permit(tenant, consent_id, admin_consent):
    return mi_settings.verify_consent_permit(tenant, consent_id, admin_consent)


def get_last_access_token():
    return mi_settings.get_access_token()


def set_access_token(token_type, access_token, expires_in):
    return mi_settings.set_access_token(token_type, access_token, expires_in)


def get_client_credentials():
    return mi_settings.get_client_credentials()

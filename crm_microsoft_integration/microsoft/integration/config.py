# App Config

## Endpoints
APP_REDIRECT_ENDPOINT = (
    "/api/method/crm_microsoft_integration.microsoft.integration.auth.permit"
)

# Microsoft Config

## Auth Config
AUTH_API_VERSION = "v2.0"

MI_AUTH_GRANT_TYPE = "client_credentials"
MI_AUTH_SCOPE = "https://graph.microsoft.com/.default"

### URIs
MI_BASE_URI = "https://login.microsoftonline.com"

### Endpoints
MI_ADMIN_CONSENT_ENDPOINT = "/adminconsent"
MI_ACESS_TOKEN_ENDPOINT = f"/oauth2/{AUTH_API_VERSION}/token"

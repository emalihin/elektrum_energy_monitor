import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

# Configuration schema for Elektrum Energy Monitor
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


class ElektrumEnergyMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Elektrum Energy Monitor."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate credentials by attempting to login
            session = requests.Session()
            token = await self.hass.async_add_executor_job(self.get_auth_token, session)

            if token:
                auth_success = await self.hass.async_add_executor_job(
                    self.authenticate,
                    user_input["username"],
                    user_input["password"],
                    token,
                    session,
                )

                if auth_success:
                    # Credentials are valid, create the entry
                    return self.async_create_entry(
                        title="Elektrum Energy Monitor", data=user_input
                    )
                else:
                    errors["base"] = "auth"
            else:
                errors["base"] = "auth"

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    def get_auth_token(self, session):
        """Retrieve the authentication token."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
        }

        try:
            r1 = session.get(
                "https://www.elektrum.lv/lv/autorizacija",
                headers=headers,
                allow_redirects=True,
            )
            if r1.status_code == 200:
                # Extract the token from the response
                tokens = self.extract_all(r1.text, 'data-token="', '"', inclusive=False)
                if tokens:
                    return tokens[1]
            _LOGGER.error("Failed to retrieve authentication token: %s", r1.status_code)
        except Exception as e:
            _LOGGER.error("Error in get_auth_token: %s", e)
        return None

    def authenticate(self, username, password, token, session):
        """Perform the authentication using the provided token and credentials."""
        login_params = {"email": username, "password": password, "captcha": ""}
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9,lv;q=0.8",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
        }

        try:
            r3 = session.post(
                "https://id.elektrum.lv/api/v1/authentication/credentials/authenticate",
                data=login_params,
                headers=headers,
            )
            if r3.status_code == 200:
                return True
            _LOGGER.error("Authentication failed: %s", r3.status_code)
        except Exception as e:
            _LOGGER.error("Error in authenticate: %s", e)

        return False

    def extract_all(self, text, start_str, end_str, inclusive=False):
        """Utility function to extract tokens from HTML."""
        results = []
        start = 0
        while True:
            start = text.find(start_str, start)
            if start == -1:
                break
            start += len(start_str)
            end = text.find(end_str, start)
            if end == -1:
                break
            if inclusive:
                results.append(text[start - len(start_str) : end + len(end_str)])
            else:
                results.append(text[start:end])
        return results

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define the options flow handler."""
        return ElektrumEnergyMonitorOptionsFlow(config_entry)


class ElektrumEnergyMonitorOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for Elektrum Energy Monitor."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return self.async_show_form(step_id="init", data_schema=CONFIG_SCHEMA)

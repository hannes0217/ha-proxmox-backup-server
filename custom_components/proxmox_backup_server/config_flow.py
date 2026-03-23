import voluptuous as vol
import aiohttp
import logging
from homeassistant import config_entries
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_TOKEN_ID, CONF_TOKEN_SECRET, CONF_VERIFY_SSL
from .api import PBSClient

_LOGGER = logging.getLogger(__name__)

class PBSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Simple check if authentication works
            client = PBSClient(
                user_input[CONF_HOST], 
                user_input[CONF_PORT], 
                user_input[CONF_USERNAME], 
                user_input[CONF_TOKEN_ID], 
                user_input[CONF_TOKEN_SECRET], 
                user_input.get(CONF_VERIFY_SSL, False)
            )
            try:
                res = await client.get_node_status()
                if res:
                    return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=8007): int,
                vol.Required(CONF_USERNAME, default="root@pam"): str,
                vol.Required(CONF_TOKEN_ID): str,
                vol.Required(CONF_TOKEN_SECRET): str,
                vol.Optional(CONF_VERIFY_SSL, default=False): bool,
            }),
            errors=errors,
        )

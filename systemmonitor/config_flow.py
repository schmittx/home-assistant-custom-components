"""Adds config flow for system monitor integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_TYPE
import homeassistant.helpers.config_validation as cv
from homeassistant.util import slugify

from .const import CONF_ARG, DOMAIN, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


class SystemMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for system monitor integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize."""

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            if user_input.get(CONF_ARG) is None and SENSOR_TYPES[user_input[CONF_TYPE]][4]:
                errors["base"] = "no_arg"
            else:
                if user_input.get(CONF_ARG) is None:
                    unique_id = title = user_input[CONF_TYPE]
                else:
                    unique_id = f"{user_input[CONF_TYPE]}_{user_input[CONF_ARG]}"
                    title = f"{user_input[CONF_TYPE]} ({user_input[CONF_ARG]})"

                await self.async_set_unique_id(slugify(unique_id))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TYPE): vol.In(SENSOR_TYPES.keys()),
                    vol.Optional(CONF_ARG): cv.string,
                }
            ),
            errors=errors,
        )

"""Adds config flow for Google Domains integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_DOMAIN, CONF_PASSWORD, CONF_TIMEOUT, CONF_USERNAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import CONF_INTERVAL, DEFAULT_INTERVAL, DEFAULT_TIMEOUT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class GoogleDomainsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Google Domains integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DOMAIN])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_DOMAIN], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DOMAIN): cv.string,
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Google Domains options callback."""
        return GoogleDomainsOptionsFlowHandler(config_entry)


class GoogleDomainsOptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options for Google Domains."""

    def __init__(self, config_entry):
        """Initialize Google Domains options flow."""
        self.options = config_entry.options

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_timeout()

    async def async_step_timeout(self, user_input=None):
        """Handle a flow initialized by the user."""
        default_interval = self.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
        default_timeout = self.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="timeout",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_INTERVAL, default=default_interval): cv.positive_int,
                    vol.Optional(CONF_TIMEOUT, default=default_timeout): cv.positive_int,
                }
            ),
        )

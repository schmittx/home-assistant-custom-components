"""Config flow for the badnest component."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
)

from .client import SonyBRAVIAClient
from .const import (
    CONF_12H,
    CONF_24H,
    CONF_EXT_SPEAKER,
    CONF_PSK,
    CONF_TIME_FORMAT,
    DEFAULT_EXT_SPEAKER,
    DEFAULT_TIME_FORMAT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SonyBRAVIADevice(config_entries.ConfigFlow, domain=DOMAIN):
    """Total Connect config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize config flow."""
        self.entry_title = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            psk = user_input[CONF_PSK]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            if await self.async_connect(host, psk):
                return self.async_create_entry(
                    title=self.entry_title, data=user_input
                )
            errors["base"] = "connect"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PSK): str,
                vol.Optional(CONF_EXT_SPEAKER, default=DEFAULT_EXT_SPEAKER): bool,
                vol.Optional(CONF_TIME_FORMAT, default=DEFAULT_TIME_FORMAT): vol.In([CONF_12H, CONF_24H]),
            },
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

#    async def async_step_import(self, user_input=None):
#        """Handle import from yaml."""
#        if await self.connect(user_input):
#            return self.async_create_entry(
#                title=self.entry_title, data=user_input
#            )

    async def async_step_import(self, user_input=None):
        """Import a config entry."""
        return await self.async_step_user(user_input)

    async def async_connect(self, host, psk):
        """Return true if the given username and password are valid."""
        client = SonyBRAVIAClient(host, psk)
        info = await self.hass.async_add_executor_job(client.connect)
        if info.get("available"):
            name, model = info.get("name"), info.get("model")
            self.entry_title = f"{name} {model} ({host})"
            return True
        return False

#    @staticmethod
#    @callback
#    def async_get_options_flow(config_entry):
#        """Get the options flow for this handler."""
#        return OptionsFlowHandler(config_entry)


#class OptionsFlowHandler(config_entries.OptionsFlow):
#    """Handle a option flow for tado."""

#    def __init__(self, config_entry: config_entries.ConfigEntry):
#        """Initialize options flow."""
#        self.config_entry = config_entry
#        self.options = {}

#    async def async_step_yaml(self, user_input=None):
#        """No options for yaml managed entries."""
#        if user_input is not None:
            # Apparently not possible to abort an options flow
            # at the moment
#            return self.async_create_entry(title="", data=self.config_entry.options)

#        return self.async_show_form(step_id="yaml")

#    async def async_step_advanced(self, user_input=None):
#        """Choose advanced options."""
#        if user_input is not None:
#            self.options.update(user_input)
#            del self.options[CONF_INCLUDE_DOMAINS]
#            return self.async_create_entry(title="", data=self.options)

#        schema_base = {}

#        if self.show_advanced_options:
#            schema_base[
#                vol.Optional(
#                    CONF_AUTO_START,
#                    default=self.options.get(
#                        CONF_AUTO_START, DEFAULT_AUTO_START
#                    ),
#                )
#            ] = bool
#        else:
#            self.options[CONF_AUTO_START] = self.options.get(
#                CONF_AUTO_START, DEFAULT_AUTO_START
#            )

#        schema_base.update(
#            {
#                vol.Optional(
#                    CONF_SAFE_MODE,
#                    default=self.options.get(CONF_SAFE_MODE, DEFAULT_SAFE_MODE),
#                ): bool
#            }
#        )

#        return self.async_show_form(
#            step_id="advanced", data_schema=vol.Schema(schema_base)
#        )

#    async def async_step_init(self, user_input=None):
#        """Handle options flow."""
#        if self.config_entry.source == SOURCE_IMPORT:
#            return await self.async_step_yaml(user_input)

#        if user_input is not None:
#            self.options.update(user_input)
#            return await self.async_step_advanced()

#        self.options = dict(self.config_entry.options)
#        entity_filter = self.options.get(CONF_FILTER, {})

#        data_schema = vol.Schema(
#            {
#                vol.Optional(
#                    CONF_INCLUDE_DOMAINS,
#                    default=entity_filter.get(CONF_INCLUDE_DOMAINS, []),
#                ): cv.multi_select(SUPPORTED_DOMAINS)
#            }
#        )
#        return self.async_show_form(step_id="init", data_schema=data_schema)

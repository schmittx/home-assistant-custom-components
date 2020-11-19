"""Adds config flow for integration component."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import DOMAIN as DOMAIN_SENSOR
from homeassistant.const import (
    CONF_NAME,
    TIME_HOURS,
)
from homeassistant.core import callback, split_entity_id
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_METHOD,
    CONF_ROUND_DIGITS,
    CONF_SOURCE_SENSOR,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_UNIT_PREFIX,
    CONF_UNIT_TIME,
    DOMAIN,
    INTEGRATION_METHODS,
    METHOD_TRAPEZOIDAL,
    PREFIX_NONE,
    UNIT_PREFIXES,
    UNIT_TIME,
)

_LOGGER = logging.getLogger(__name__)


class IntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for integration component."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize."""

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        all_sensors = await self.hass.async_add_executor_job(_get_all_sensor_entities, self.hass)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOURCE_SENSOR): vol.In(all_sensors),
                    vol.Required(CONF_NAME): cv.string,
                    vol.Optional(CONF_ROUND_DIGITS, default=3): vol.In(list(range(0, 4))),
                    vol.Optional(CONF_UNIT_PREFIX, default=PREFIX_NONE): vol.In(UNIT_PREFIXES.keys()),
                    vol.Optional(CONF_UNIT_TIME, default=TIME_HOURS): vol.In(UNIT_TIME.keys()),
                    vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
                    vol.Optional(CONF_METHOD, default=METHOD_TRAPEZOIDAL): vol.In(INTEGRATION_METHODS),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Integration options callback."""
        return IntegrationOptionsFlowHandler(config_entry)


class IntegrationOptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options for the integration component."""

    def __init__(self, config_entry):
        """Initialize integration options flow."""
        self.config_entry = config_entry
        self.data = config_entry.data
        self.options = config_entry.options

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            current_title = self.config_entry.title
            default_title = self.data[CONF_NAME]
            updated_title = user_input[CONF_NAME]
            title = current_title if current_title != default_title else updated_title
            return self.async_create_entry(title=title, data=user_input)

        source_sensor = self.options.get(CONF_SOURCE_SENSOR, self.data[CONF_SOURCE_SENSOR])
        name = self.options.get(CONF_NAME, self.data[CONF_NAME])
        round_digits = self.options.get(CONF_ROUND_DIGITS, self.data[CONF_ROUND_DIGITS])
        unit_prefix = self.options.get(CONF_UNIT_PREFIX, self.data[CONF_UNIT_PREFIX])
        unit_time = self.options.get(CONF_UNIT_TIME, self.data[CONF_UNIT_TIME])
        unit_of_measurement = self.options.get(CONF_UNIT_OF_MEASUREMENT, self.data.get(CONF_UNIT_OF_MEASUREMENT))
        method = self.options.get(CONF_METHOD, self.data[CONF_METHOD])

        all_sensors = await self.hass.async_add_executor_job(_get_all_sensor_entities, self.hass)
        if unit_of_measurement:
            unit_of_measurement_schema = vol.Optional(CONF_UNIT_OF_MEASUREMENT, default=unit_of_measurement)
        else:
            unit_of_measurement_schema = vol.Optional(CONF_UNIT_OF_MEASUREMENT)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOURCE_SENSOR, default=source_sensor): vol.In(all_sensors),
                    vol.Required(CONF_NAME, default=name): cv.string,
                    vol.Optional(CONF_ROUND_DIGITS, default=round_digits): vol.In(list(range(0, 4))),
                    vol.Optional(CONF_UNIT_PREFIX, default=unit_prefix): vol.In(UNIT_PREFIXES.keys()),
                    vol.Optional(CONF_UNIT_TIME, default=unit_time): vol.In(UNIT_TIME.keys()),
                    unit_of_measurement_schema: cv.string,
                    vol.Optional(CONF_METHOD, default=method): vol.In(INTEGRATION_METHODS),
                }
            ),
        )


def _get_all_sensor_entities(hass):
    """List entities in the sensor domain."""
    entity_ids = [
        state.entity_id
        for state in hass.states.all()
        if (split_entity_id(state.entity_id))[0] == DOMAIN_SENSOR
    ]
    entity_ids.sort()
    return entity_ids

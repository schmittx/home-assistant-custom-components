"""Custom Component"""

"""Class to hold all custom accessories."""
import logging

from pyhap.const import CATEGORY_SENSOR

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_UNIT_OF_MEASUREMENT,
    TEMP_CELSIUS,
)
from homeassistant.core import callback

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_CURRENT_TEMPERATURE,
    CHAR_NAME,
    CHAR_STATUS_LOW_BATTERY,
    CONF_SERVICE_NAME_PREFIX,
    PROP_CELSIUS,
    SERV_TEMPERATURE_SENSOR,
)
from .util import convert_to_float, temperature_to_homekit

_LOGGER = logging.getLogger(__name__)


@TYPES.register("NestTemperatureSensor")
class NestTemperatureSensor(HomeAccessory):
    """Generate a NestTemperatureSensor accessory."""

    def __init__(self, *args):
        """Initialize a NestProtect accessory object."""
        super().__init__(*args, category=CATEGORY_SENSOR)
        state = self.hass.states.get(self.entity_id)
        prefix = self.config.get(CONF_SERVICE_NAME_PREFIX, self.display_name)

        temp_chars = [
            CHAR_NAME,
            CHAR_STATUS_LOW_BATTERY,
            CHAR_CURRENT_TEMPERATURE,
        ]
        serv_temp = self.add_preload_service(
            SERV_TEMPERATURE_SENSOR, temp_chars,
        )
        serv_temp.configure_char(
            CHAR_NAME, value=f"{prefix} Temperature",
        )
        self.char_temp_low_battery = serv_temp.configure_char(
            CHAR_STATUS_LOW_BATTERY, value=0,
        )
        self.char_current_temp = serv_temp.configure_char(
            CHAR_CURRENT_TEMPERATURE, value=0, properties=PROP_CELSIUS,
        )
        # Set the state so it is in sync on initial
        # GET to avoid an event storm after homekit startup
        self.async_update_state(state)

    @callback
    def async_update_state(self, new_state):
        """Update accessory after state change."""
        attrs = new_state.attributes

        unit = attrs.get(ATTR_UNIT_OF_MEASUREMENT, TEMP_CELSIUS)
        temperature = convert_to_float(new_state.state)
        if isinstance(temperature, (float, int)):
            hk_temp = temperature_to_homekit(temperature, unit)
            if self.char_current_temp.value != hk_temp:
                self.char_current_temp.set_value(hk_temp)

        battery_level = convert_to_float(attrs.get(ATTR_BATTERY_LEVEL))
        if isinstance(battery_level, (float, int)):
            is_low_battery = 1 if battery_level < self.low_battery_threshold else 0
            if self.char_temp_low_battery.value != is_low_battery:
                self.char_temp_low_battery.set_value(is_low_battery)

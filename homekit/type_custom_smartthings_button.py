"""Custom Component"""

"""Class to hold all custom accessories."""
import logging

from pyhap.const import CATEGORY_PROGRAMMABLE_SWITCH

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_TEMPERATURE,
    STATE_ON,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import callback

from .accessories import TYPES, HomeAccessory
from .const import (
    ATTR_LAST_ACTION,
    CHAR_CURRENT_TEMPERATURE,
    CHAR_NAME,
    CHAR_PROGRAMMABLE_SWITCH_EVENT,
    CHAR_STATUS_LOW_BATTERY,
    CONF_SERVICE_NAME_PREFIX,
    SERV_STATELESS_PROGRAMMABLE_SWITCH,
    SERV_TEMPERATURE_SENSOR,
)
from .util import convert_to_float, temperature_to_homekit

SWITCH_EVENT_MAP = {
    "pushed": 0,
    "double": 1,
    "held": 2,
}

_LOGGER = logging.getLogger(__name__)


@TYPES.register("SmartThingsButton")
class SmartThingsButton(HomeAccessory):
    """Generate a SmartThingsButton accessory."""

    def __init__(self, *args):
        """Initialize a SmartThingsButton accessory object."""
        super().__init__(*args, category=CATEGORY_PROGRAMMABLE_SWITCH)
        state = self.hass.states.get(self.entity_id)
        prefix = self.config.get(CONF_SERVICE_NAME_PREFIX, self.display_name)

        switch_chars = [
            CHAR_NAME,
            CHAR_PROGRAMMABLE_SWITCH_EVENT,
        ]
        serv_switch = self.add_preload_service(
            SERV_STATELESS_PROGRAMMABLE_SWITCH, switch_chars,
        )
        serv_switch.configure_char(
            CHAR_NAME, value=f"{prefix} Switch",
        )
        self.char_switch_event = serv_switch.configure_char(
            CHAR_PROGRAMMABLE_SWITCH_EVENT,
        )

        temperature_chars = [
            CHAR_NAME,
            CHAR_STATUS_LOW_BATTERY,
            CHAR_CURRENT_TEMPERATURE,
        ]
        serv_temperature = self.add_preload_service(
            SERV_TEMPERATURE_SENSOR, temperature_chars,
        )
        serv_temperature.configure_char(
            CHAR_NAME, value=f"{prefix} Temperature",
        )
        self.char_temperature_low_battery = serv_temperature.configure_char(
            CHAR_STATUS_LOW_BATTERY, value=0,
        )
        self.char_temperature = serv_temperature.configure_char(
            CHAR_CURRENT_TEMPERATURE, value=0,
        )
        # Set the state so it is in sync on initial
        # GET to avoid an event storm after homekit startup
        self.async_update_state(state)

    @callback
    def async_update_state(self, new_state):
        """Update accessory after state change."""
        attrs = new_state.attributes

        battery_level = convert_to_float(attrs.get(ATTR_BATTERY_LEVEL))
        if isinstance(battery_level, (int, float)):
            low_battery = battery_level < self.low_battery_threshold
            if self.char_temperature_low_battery.value != low_battery:
                self.char_temperature_low_battery.set_value(low_battery)

        switch_event = SWITCH_EVENT_MAP[attrs.get(ATTR_LAST_ACTION)]
        if new_state.state == STATE_ON:
            self.char_switch_event.set_value(switch_event)

        temperature = temperature_to_homekit(convert_to_float(attrs.get(ATTR_TEMPERATURE)), TEMP_FAHRENHEIT)
        if isinstance(temperature, (int, float)) and self.char_temperature.value != temperature:
            self.char_temperature.set_value(temperature)

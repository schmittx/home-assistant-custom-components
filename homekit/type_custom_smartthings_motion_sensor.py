"""Custom Component"""

"""Class to hold all custom accessories."""
import logging

from pyhap.const import CATEGORY_SENSOR

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_TEMPERATURE,
    STATE_ON,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import callback

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_CURRENT_TEMPERATURE,
    CHAR_MOTION_DETECTED,
    CHAR_NAME,
    CHAR_STATUS_LOW_BATTERY,
    CONF_SERVICE_NAME_PREFIX,
    SERV_MOTION_SENSOR,
    SERV_TEMPERATURE_SENSOR,
)
from .util import convert_to_float, temperature_to_homekit

_LOGGER = logging.getLogger(__name__)


@TYPES.register("SmartThingsMotionSensor")
class SmartThingsMotionSensor(HomeAccessory):
    """Generate a SmartThingsMotionSensor accessory."""

    def __init__(self, *args):
        """Initialize a SmartThingsMotionSensor accessory object."""
        super().__init__(*args, category=CATEGORY_SENSOR)
        state = self.hass.states.get(self.entity_id)
        prefix = self.config.get(CONF_SERVICE_NAME_PREFIX, self.display_name)

        motion_chars = [
            CHAR_NAME,
            CHAR_STATUS_LOW_BATTERY,
            CHAR_MOTION_DETECTED,
        ]
        serv_motion = self.add_preload_service(
            SERV_MOTION_SENSOR, motion_chars,
        )
        serv_motion.configure_char(
            CHAR_NAME, value=f"{prefix} Motion",
        )
        self.char_motion_low_battery = serv_motion.configure_char(
            CHAR_STATUS_LOW_BATTERY, value=0,
        )
        self.char_motion_detected = serv_motion.configure_char(
            CHAR_MOTION_DETECTED, value=0,
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
            if self.char_motion_low_battery.value != low_battery:
                self.char_motion_low_battery.set_value(low_battery)
            if self.char_temperature_low_battery.value != low_battery:
                self.char_temperature_low_battery.set_value(low_battery)

        motion_detected = new_state.state == STATE_ON
        if isinstance(motion_detected, bool) and self.char_motion_detected.value != motion_detected:
            self.char_motion_detected.set_value(motion_detected)

        temperature = temperature_to_homekit(convert_to_float(attrs.get(ATTR_TEMPERATURE)), TEMP_FAHRENHEIT)
        if isinstance(temperature, (int, float)) and self.char_temperature.value != temperature:
            self.char_temperature.set_value(temperature)

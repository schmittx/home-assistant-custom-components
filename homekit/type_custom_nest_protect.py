"""Custom Component"""

"""Class to hold all custom accessories."""
import logging

from pyhap.const import CATEGORY_SENSOR

from custom_components.nest.const import (
    ATTR_BATTERY_HEALTH,
    ATTR_CO_STATUS,
    ATTR_ONLINE,
    ATTR_SMOKE_STATUS,
    STATE_EMERGENCY,
    STATE_OK,
    STATE_REPLACE,
    STATE_WARNING,
)
from homeassistant.core import callback

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_CARBON_MONOXIDE_DETECTED,
    CHAR_NAME,
    CHAR_SMOKE_DETECTED,
    CHAR_STATUS_ACTIVE,
    CHAR_STATUS_LOW_BATTERY,
    CONF_SERVICE_NAME_PREFIX,
    SERV_CARBON_MONOXIDE_SENSOR,
    SERV_MOTION_SENSOR,
    SERV_SMOKE_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

LOW_BATTERY_MAP = {
    STATE_OK: 0,
    STATE_REPLACE: 1,
}

STATE_DETECTED_MAP = {
    STATE_OK: 0,
    STATE_WARNING: 1,
    STATE_EMERGENCY: 1,
}


@TYPES.register("NestProtect")
class NestProtect(HomeAccessory):
    """Generate a NestProtect accessory."""

    def __init__(self, *args):
        """Initialize a NestProtect accessory object."""
        super().__init__(*args, category=CATEGORY_SENSOR)
        state = self.hass.states.get(self.entity_id)
        prefix = self.config.get(CONF_SERVICE_NAME_PREFIX, self.display_name)

        co_chars = [
            CHAR_NAME,
            CHAR_STATUS_ACTIVE,
            CHAR_STATUS_LOW_BATTERY,
            CHAR_CARBON_MONOXIDE_DETECTED,
        ]
        serv_co = self.add_preload_service(
            SERV_CARBON_MONOXIDE_SENSOR, co_chars,
        )
        serv_co.configure_char(
            CHAR_NAME, value=f"{prefix} Carbon Monoxide",
        )
        self.char_co_active = serv_co.configure_char(
            CHAR_STATUS_ACTIVE, value=0,
        )
        self.char_co_low_battery = serv_co.configure_char(
            CHAR_STATUS_LOW_BATTERY, value=0,
        )
        self.char_co_detected = serv_co.configure_char(
            CHAR_CARBON_MONOXIDE_DETECTED, value=0,
        )

        smoke_chars = [
            CHAR_NAME,
            CHAR_STATUS_ACTIVE,
            CHAR_STATUS_LOW_BATTERY,
            CHAR_SMOKE_DETECTED,
        ]
        serv_smoke = self.add_preload_service(
            SERV_SMOKE_SENSOR, smoke_chars,
        )
        serv_smoke.configure_char(
            CHAR_NAME, value=f"{prefix} Smoke",
        )
        self.char_smoke_active = serv_smoke.configure_char(
            CHAR_STATUS_ACTIVE, value=0,
        )
        self.char_smoke_low_battery = serv_smoke.configure_char(
            CHAR_STATUS_LOW_BATTERY, value=0,
        )
        self.char_smoke_detected = serv_smoke.configure_char(
            CHAR_SMOKE_DETECTED, value=0,
        )

        # Set the state so it is in sync on initial
        # GET to avoid an event storm after homekit startup
        self.async_update_state(state)

    @callback
    def async_update_state(self, new_state):
        """Update accessory after state change."""
        attrs = new_state.attributes

        active = attrs.get(ATTR_ONLINE)
        if isinstance(active, bool):
            if self.char_co_active.value != active:
                self.char_co_active.set_value(active)
            if self.char_smoke_active.value != active:
                self.char_smoke_active.set_value(active)

        battery_health = attrs.get(ATTR_BATTERY_HEALTH)
        if battery_health in LOW_BATTERY_MAP:
            low_battery = LOW_BATTERY_MAP[battery_health]
            if self.char_co_low_battery.value != low_battery:
                self.char_co_low_battery.set_value(low_battery)
            if self.char_smoke_low_battery.value != low_battery:
                self.char_smoke_low_battery.set_value(low_battery)

        co_status = attrs.get(ATTR_CO_STATUS)
        if co_status in STATE_DETECTED_MAP:
            co_detected = STATE_DETECTED_MAP[co_status]
            if self.char_co_detected.value != co_detected:
                self.char_co_detected.set_value(co_detected)

        smoke_status = attrs.get(ATTR_SMOKE_STATUS)
        if smoke_status in STATE_DETECTED_MAP:
            smoke_detected = STATE_DETECTED_MAP[smoke_status]
            if self.char_smoke_detected.value != smoke_detected:
                self.char_smoke_detected.set_value(smoke_detected)

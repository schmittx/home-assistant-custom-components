"""Custom Component"""

"""Class to hold all custom accessories."""
import logging

from pyhap.const import CATEGORY_SENSOR

from custom_components.nest.const import (
    ATTR_ACTIVITY_DETECTED,
    ATTR_MOTION_DETECTED,
    ATTR_ONLINE,
    ATTR_PERSON_DETECTED,
)
from homeassistant.core import callback

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_MOTION_DETECTED,
    CHAR_NAME,
    CHAR_OCCUPANCY_DETECTED,
    CHAR_STATUS_ACTIVE,
    CONF_SERVICE_NAME_PREFIX,
    SERV_MOTION_SENSOR,
    SERV_OCCUPANCY_SENSOR,
)

_LOGGER = logging.getLogger(__name__)


@TYPES.register("NestCameraSensor")
class NestCameraSensor(HomeAccessory):
    """Generate a NestCameraSensor accessory."""

    def __init__(self, *args):
        """Initialize a NestCameraSensor accessory object."""
        super().__init__(*args, category=CATEGORY_SENSOR)
        state = self.hass.states.get(self.entity_id)
        prefix = self.config.get(CONF_SERVICE_NAME_PREFIX, self.display_name)

        motion_chars = [
            CHAR_NAME,
            CHAR_STATUS_ACTIVE,
            CHAR_MOTION_DETECTED,
        ]
        serv_motion = self.add_preload_service(
            SERV_MOTION_SENSOR, motion_chars,
        )
        serv_motion.configure_char(
            CHAR_NAME, value=f"{prefix} Motion",
        )
        self.char_motion_active = serv_motion.configure_char(
            CHAR_STATUS_ACTIVE, value=0,
        )
        self.char_motion_detected = serv_motion.configure_char(
            CHAR_MOTION_DETECTED, value=0,
        )

        occupancy_chars = [
            CHAR_NAME,
            CHAR_STATUS_ACTIVE,
            CHAR_OCCUPANCY_DETECTED,
        ]
        serv_occupancy = self.add_preload_service(
            SERV_OCCUPANCY_SENSOR, occupancy_chars,
        )
        serv_occupancy.configure_char(
            CHAR_NAME, value=f"{prefix} Occupancy",
        )
        self.char_occupancy_active = serv_occupancy.configure_char(
            CHAR_STATUS_ACTIVE, value=0,
        )
        self.char_occupancy_detected = serv_occupancy.configure_char(
            CHAR_OCCUPANCY_DETECTED, value=0,
        )
        self._activity_zones = [attr for attr, value in state.attributes.items() if ATTR_ACTIVITY_DETECTED in attr]

        serv_activity_zones = {}
        self.char_activity_zones_active = {}
        self.char_activity_zones_detected = {}
        for zone in self._activity_zones:
            serv_activity_zones[zone] = self.add_preload_service(
                SERV_MOTION_SENSOR, motion_chars,
            )
            name = zone.replace(f"_{ATTR_ACTIVITY_DETECTED}", "").replace("_", " ").title()
            serv_activity_zones[zone].configure_char(
                CHAR_NAME, value=f"{prefix} {name} Motion",
            )
            self.char_activity_zones_active[zone] = serv_activity_zones[zone].configure_char(
                CHAR_STATUS_ACTIVE, value=0,
            )
            self.char_activity_zones_detected[zone] = serv_activity_zones[zone].configure_char(
                CHAR_MOTION_DETECTED, value=0,
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
            if self.char_motion_active.value != active:
                self.char_motion_active.set_value(active)
            if self.char_occupancy_active.value != active:
                self.char_occupancy_active.set_value(active)

        motion_detected = attrs.get(ATTR_MOTION_DETECTED)
        if isinstance(motion_detected, bool) and self.char_motion_detected.value != motion_detected:
            self.char_motion_detected.set_value(motion_detected)

        occupancy_detected = attrs.get(ATTR_PERSON_DETECTED)
        if isinstance(occupancy_detected, bool) and self.char_occupancy_detected.value != occupancy_detected:
            self.char_occupancy_detected.set_value(occupancy_detected)

        for zone in self._activity_zones:
            if isinstance(active, bool) and self.char_activity_zones_active[zone].value != active:
                self.char_activity_zones_active[zone].set_value(active)

            zone_activity_detected = attrs.get(f"{zone}")
            if isinstance(zone_activity_detected, bool) and self.char_activity_zones_detected[zone].value != zone_activity_detected:
                self.char_activity_zones_detected[zone].set_value(zone_activity_detected)

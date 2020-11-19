"""Custom Component"""

"""Class to hold all fan accessories."""
import logging

from pyhap.const import CATEGORY_FAN

from homeassistant.components.fan import (
    ATTR_DIRECTION,
    ATTR_SPEED,
    ATTR_SPEED_LIST,
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    DOMAIN,
    SERVICE_SET_DIRECTION,
    SERVICE_SET_SPEED,
    SPEED_OFF,
    SUPPORT_DIRECTION,
    SUPPORT_SET_SPEED,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import callback

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_ON,
    CHAR_ROTATION_DIRECTION,
    CHAR_ROTATION_SPEED,
    PROP_MIN_STEP,
    SERV_FAN,
)

_LOGGER = logging.getLogger(__name__)


@TYPES.register("Fan")
class Fan(HomeAccessory):
    """Generate a Fan accessory for a fan entity.

    Currently supports: state, speed, oscillate, direction.
    """

    def __init__(self, *args):
        """Initialize a new Light accessory object."""
        super().__init__(*args, category=CATEGORY_FAN)

        self.chars = []
        state = self.hass.states.get(self.entity_id)

        features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        if features & SUPPORT_DIRECTION:
            self.chars.append(CHAR_ROTATION_DIRECTION)
        if features & SUPPORT_SET_SPEED:
            self.chars.append(CHAR_ROTATION_SPEED)

        serv_fan = self.add_preload_service(SERV_FAN, self.chars)

        self.char_on = serv_fan.configure_char(CHAR_ON, value=0)

        if CHAR_ROTATION_DIRECTION in self.chars:
            self.char_direction = serv_fan.configure_char(CHAR_ROTATION_DIRECTION, value=0)

        if CHAR_ROTATION_SPEED in self.chars:
            self.speed_list = state.attributes.get(ATTR_SPEED_LIST)

            if self.speed_list:
                self.min_step = 100 / (len(self.speed_list) - 1)
#                self.min_step = 100 / len(self.speed_list)
            else:
                self.min_step = 1

            self.char_speed = serv_fan.configure_char(
                CHAR_ROTATION_SPEED,
                value=100,
                properties={PROP_MIN_STEP: self.min_step},
            )
        self.async_update_state(state)

        serv_fan.setter_callback = self._set_chars

    def _set_chars(self, char_values):
        _LOGGER.debug("Fan _set_chars: %s", char_values)
        if CHAR_ON in char_values:
            if char_values[CHAR_ON]:
                # If the device supports set speed we
                # do not want to turn on as it will take
                # the fan to 100% than to the desired speed.
                #
                # Setting the speed will take care of turning
                # on the fan if SUPPORT_SET_SPEED is set.
                if CHAR_ROTATION_SPEED not in self.chars or CHAR_ROTATION_SPEED not in char_values:
                    self.set_state(1)
            else:
                # Its off, nothing more to do as setting the
                # other chars will likely turn it back on which
                # is what we want to avoid
                self.set_state(0)
                return

        if CHAR_ROTATION_DIRECTION in char_values:
            self.set_direction(char_values[CHAR_ROTATION_DIRECTION])

        # We always do this LAST to ensure they
        # get the speed they asked for
        if CHAR_ROTATION_SPEED in char_values:
            self.set_speed(char_values[CHAR_ROTATION_SPEED])

    def set_state(self, value):
        """Set state if call came from HomeKit."""
        _LOGGER.debug("%s: Set state to %d", self.entity_id, value)
        service = SERVICE_TURN_ON if value == 1 else SERVICE_TURN_OFF
        params = {ATTR_ENTITY_ID: self.entity_id}
        self.call_service(DOMAIN, service, params)

    def set_direction(self, value):
        """Set state if call came from HomeKit."""
        _LOGGER.debug("%s: Set direction to %d", self.entity_id, value)
        direction = DIRECTION_REVERSE if value == 1 else DIRECTION_FORWARD
        params = {ATTR_ENTITY_ID: self.entity_id, ATTR_DIRECTION: direction}
        self.call_service(DOMAIN, SERVICE_SET_DIRECTION, params, direction)

    def set_speed(self, value):
        """Set state if call came from HomeKit."""
        _LOGGER.debug("%s: Set speed to %d", self.entity_id, value)
#        self._flag[CHAR_ROTATION_SPEED] = True
#        speed = self.speed_list[(int(round(value / self.min_step)) - 1)]
#        params = {ATTR_ENTITY_ID: self.entity_id, ATTR_SPEED: speed}
#        self.call_service(DOMAIN, SERVICE_SET_SPEED, params, f"speed at {speed}%")
        if value == 0:
            self.set_state(0)
        else:
            speed = self.speed_list[int(round(value / self.min_step))]
            params = {ATTR_ENTITY_ID: self.entity_id, ATTR_SPEED: speed}
            self.call_service(DOMAIN, SERVICE_SET_SPEED, params, f"speed at {speed}%")

    @callback
    def async_update_state(self, new_state):
        """Update fan after state change."""
        # Handle State
        state = new_state.state
        if state == STATE_ON and self.char_on.value != 1:
            self.char_on.set_value(1)
        elif state == STATE_OFF and self.char_on.value != 0:
            self.char_on.set_value(0)

        # Handle Direction
        if CHAR_ROTATION_DIRECTION in self.chars:
            direction = new_state.attributes.get(ATTR_DIRECTION)
            if direction in (DIRECTION_FORWARD, DIRECTION_REVERSE):
                hk_direction = 1 if direction == DIRECTION_REVERSE else 0
                if self.char_direction.value != hk_direction:
                    self.char_direction.set_value(hk_direction)

        # Handle Speed
        if CHAR_ROTATION_SPEED in self.chars and state != STATE_OFF:
            # We do not change the homekit speed when turning off
            # as it will clear the restore state
            speed = new_state.attributes.get(ATTR_SPEED)
            if isinstance(speed, str):
                hk_speed = self.speed_list.index(speed) * self.min_step
                if self.char_speed.value != hk_speed:
                    self.char_speed.set_value(hk_speed)

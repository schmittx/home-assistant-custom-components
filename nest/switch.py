"""Custom Component"""

"""Support for Nest switches."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_HOME

from . import NestDevice
from .const import (
    DATA_NEST,
    DOMAIN as NEST_DOMAIN,
    STATE_AWAY,
    TYPE_CAMERA,
    TYPE_STRUCTURE,
)

_LOGGER = logging.getLogger(__name__)

SWITCH_TYPES = {
    "away": [TYPE_STRUCTURE, "Away", "mdi:home"],
    "is_streaming": [TYPE_CAMERA, "Streaming", "mdi:video"],
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Nest binary sensors.

    No longer used.
    """


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up a Nest binary sensor based on a config entry."""
    nest = hass.data[NEST_DOMAIN][DATA_NEST]

    def get_switches():
        """Get the Nest switches."""
        switches = []

        for structure in nest.structures():
            for variable in SWITCH_TYPES:
                if SWITCH_TYPES[variable][0] == TYPE_STRUCTURE:
                    switches.append(NestSwitch(structure, None, variable))

        for structure, device in nest.cameras():
            for variable in SWITCH_TYPES:
                if SWITCH_TYPES[variable][0] == TYPE_CAMERA:
                    switches.append(NestSwitch(structure, device, variable))

        return switches

    async_add_entities(await hass.async_add_job(get_switches), True)


class NestSwitch(SwitchEntity, NestDevice):
    """Representation of a Nest binary sensor."""

    def __init__(self, structure, device, variable):
        """Initialize the sensor."""
        super().__init__(structure, device)
        self.variable = variable
        if device:
            self._name = f"{self.device.name_long} {SWITCH_TYPES[self.variable][1]}"
        else:
            self._name = f"{self.structure.name} Nest {SWITCH_TYPES[self.variable][1]}"

        self._state = None
        self._unique_id = f"{self.device.serial}-{self.variable}"

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return SWITCH_TYPES[self.variable][2]

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    def update(self):
        """Retrieve latest state."""
        if self.variable == "away":
            value = getattr(self.device, self.variable)
            self._state = bool(value == STATE_AWAY)

        else:
            self._state = bool(getattr(self.device, self.variable))

    def turn_on(self, **kwargs):
        """Turn the device on."""
        if self.variable == "away":
            self.device.away = STATE_AWAY

        else:
            if not self.device.online:
                _LOGGER.error(f"{self._name} is offline")
                return
            self.device.is_streaming = True

    def turn_off(self, **kwargs):
        """Turn the device off."""
        if self.variable == "away":
            self.device.away = STATE_HOME

        else:
            if not self.device.online:
                _LOGGER.error(f"{self._name} is offline")
                return
            self.device.is_streaming = False

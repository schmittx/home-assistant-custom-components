"""Custom Component"""

"""Support for binary sensors through the SmartThings cloud API."""
from typing import Optional, Sequence

from pysmartthings import Attribute, Capability

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_OPENING,
    DEVICE_CLASS_PRESENCE,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SOUND,
    BinarySensorEntity,
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later

from . import SmartThingsEntity
from .const import DATA_BROKERS, DOMAIN, SIGNAL_SMARTTHINGS_BUTTON, SIGNAL_SMARTTHINGS_UPDATE

CAPABILITY_TO_ATTRIB = {
    Capability.acceleration_sensor: Attribute.acceleration,
    Capability.button: Attribute.button,
    Capability.contact_sensor: Attribute.contact,
    Capability.filter_status: Attribute.filter_status,
    Capability.motion_sensor: Attribute.motion,
    Capability.presence_sensor: Attribute.presence,
    Capability.sound_sensor: Attribute.sound,
    Capability.tamper_alert: Attribute.tamper,
    Capability.valve: Attribute.valve,
    Capability.water_sensor: Attribute.water,
}
ATTRIB_TO_CLASS = {
    Attribute.acceleration: "moving",
    Attribute.button: None,
    Attribute.contact: DEVICE_CLASS_OPENING,
    Attribute.filter_status: DEVICE_CLASS_PROBLEM,
    Attribute.motion: DEVICE_CLASS_MOTION,
    Attribute.presence: DEVICE_CLASS_PRESENCE,
    Attribute.sound: DEVICE_CLASS_SOUND,
    Attribute.tamper: DEVICE_CLASS_PROBLEM,
    Attribute.valve: DEVICE_CLASS_OPENING,
    Attribute.water: "moisture",
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add binary sensors for a config entry."""
    broker = hass.data[DOMAIN][DATA_BROKERS][config_entry.entry_id]
    sensors = []
    for device in broker.devices.values():
        for capability in broker.get_assigned(device.device_id, "binary_sensor"):
            attrib = CAPABILITY_TO_ATTRIB[capability]
            # Custom Component
            if attrib == Attribute.button:
                sensors.append(SmartThingsButtonBinarySensor(device, attrib))
            else:
            # Custom Component
                sensors.append(SmartThingsBinarySensor(device, attrib))
    async_add_entities(sensors)


def get_capabilities(capabilities: Sequence[str]) -> Optional[Sequence[str]]:
    """Return all capabilities supported if minimum required are present."""
    return [
        capability for capability in CAPABILITY_TO_ATTRIB if capability in capabilities
    ]


class SmartThingsBinarySensor(SmartThingsEntity, BinarySensorEntity):
    """Define a SmartThings Binary Sensor."""

    def __init__(self, device, attribute):
        """Init the class."""
        super().__init__(device)
        self._attribute = attribute

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        # Custom Component
        return f"{self._device.label} {self._attribute.title()}"
        # Custom Component

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._device.device_id}.{self._attribute}"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._device.status.is_on(self._attribute)

    @property
    def device_class(self):
        """Return the class of this device."""
        return ATTRIB_TO_CLASS[self._attribute]

    # Custom Component
    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        state_attrs = super().device_state_attributes
        temperature = self._device.status.attributes[Attribute.temperature].value
        if temperature is not None:
            state_attrs[ATTR_TEMPERATURE] = temperature
        return state_attrs
    # Custom Component


# Custom Component
class SmartThingsButtonBinarySensor(SmartThingsBinarySensor):
    """Define a SmartThings Button Binary Sensor."""

    def __init__(self, device, attribute):
        """Init the class."""
        super().__init__(device, attribute)
        self._button_dispatcher_remove = None
        self._update_dispatcher_remove = None
        self._delay_listener = None
        self._state = None

    async def async_added_to_hass(self):
        """Device added to hass."""

        async def async_update_state(devices):
            """Update device state."""
            if self._device.device_id in devices:

                self._state = self._device.status.attributes[self._attribute].value in ["pushed", "double", "held"]

                if self._state:

                    def off_delay_listener(now):
                        """Switch device off after a delay."""
                        self._delay_listener = None
                        self._state = False
                        self.async_write_ha_state()

                    if self._delay_listener is not None:
                        self._delay_listener()
                    self._delay_listener = async_call_later(
                        self.hass, 3, off_delay_listener
                    )

                await self.async_update_ha_state(True)

        async def async_update_attrs(devices):
            """Update device state."""
            if self._device.device_id in devices:
                await self.async_update_ha_state(True)

        self._button_dispatcher_remove = async_dispatcher_connect(
            self.hass, SIGNAL_SMARTTHINGS_BUTTON, async_update_state
        )

        self._update_dispatcher_remove = async_dispatcher_connect(
            self.hass, SIGNAL_SMARTTHINGS_UPDATE, async_update_attrs
        )

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect the device when removed."""
        if self._button_dispatcher_remove:
            self._button_dispatcher_remove()
        if self._update_dispatcher_remove:
            self._update_dispatcher_remove()

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self._device.label} Pressed"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        state_attrs = super().device_state_attributes
        last_action = self._device.status.attributes[self._attribute].value
        if last_action is not None:
            state_attrs["last_action"] = last_action
        return state_attrs
# Custom Component

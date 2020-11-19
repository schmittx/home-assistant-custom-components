"""Custom Component"""

"""Support for Nest binary sensors."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_HEAT,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_SOUND,
)

from . import NestDevice
from .const import (
    ATTR_ACTIVITY_DETECTED,
    ATTR_BATTERY_HEALTH,
    ATTR_CO_STATUS,
    ATTR_COLOR_STATUS,
    ATTR_MOTION_DETECTED,
    ATTR_ONLINE,
    ATTR_PERSON_DETECTED,
    ATTR_SMOKE_STATUS,
    ATTR_SOUND_DETECTED,
    DATA_NEST,
    DOMAIN as NEST_DOMAIN,
    STATE_AWAY,
    STATE_GREEN,
    STATE_OK,
    TYPE_ALL,
    TYPE_CAMERA,
    TYPE_SMOKE_CO_ALARM,
    TYPE_STRUCTURE,
    TYPE_THERMOSTAT,
)

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_TYPES = {
    "activity_zone": [TYPE_CAMERA, "Activity", DEVICE_CLASS_MOTION],
    "away": [TYPE_STRUCTURE, "Away", None],
    "battery_low": [TYPE_SMOKE_CO_ALARM, "Battery Low", DEVICE_CLASS_BATTERY],
    "camera_status": [TYPE_CAMERA, "Status", DEVICE_CLASS_PROBLEM],
    "co_detected": [TYPE_SMOKE_CO_ALARM, "CO Detected", DEVICE_CLASS_GAS],
    "fan": [TYPE_THERMOSTAT, "Fan", None],
    "has_leaf": [TYPE_THERMOSTAT, "Has Leaf", None],
    "is_locked": [TYPE_THERMOSTAT, "Is Locked", None],
    "is_using_emergency_heat": [TYPE_THERMOSTAT, "Is Using Emergency Heat", DEVICE_CLASS_HEAT],
    "motion_detected": [TYPE_CAMERA, "Motion Detected", DEVICE_CLASS_MOTION],
    "online": [TYPE_ALL, "Online", DEVICE_CLASS_CONNECTIVITY],
    "person_detected": [TYPE_CAMERA, "Person Detected", DEVICE_CLASS_OCCUPANCY],
    "protect_status": [TYPE_SMOKE_CO_ALARM, "Status", DEVICE_CLASS_PROBLEM],
    "security_state": [TYPE_STRUCTURE, "Security State", DEVICE_CLASS_SAFETY],
    "smoke_detected": [TYPE_SMOKE_CO_ALARM, "Smoke Detected", DEVICE_CLASS_SMOKE],
    "sound_detected": [TYPE_CAMERA, "Sound Detected", DEVICE_CLASS_SOUND],
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Nest binary sensors.

    No longer used.
    """


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up a Nest binary sensor based on a config entry."""
    nest = hass.data[NEST_DOMAIN][DATA_NEST]

    def get_binary_sensors():
        """Get the Nest binary sensors."""
        binary_sensors = []

        for structure in nest.structures():
            for variable in BINARY_SENSOR_TYPES:
                if BINARY_SENSOR_TYPES[variable][0] == TYPE_STRUCTURE:
                    binary_sensors.append(
                        NestBinarySensor(structure, None, variable))

        for structure, device in nest.cameras():
            for variable in BINARY_SENSOR_TYPES:
                if BINARY_SENSOR_TYPES[variable][0] in [TYPE_ALL, TYPE_CAMERA]:
                    if variable == "activity_zone":
                        for zone in device.activity_zones:
                            binary_sensors.append(
                                NestActivityZoneSensor(
                                    structure, device, variable, zone))
                    else:
                        binary_sensors.append(
                            NestBinarySensor(structure, device, variable))

        for structure, device in nest.smoke_co_alarms():
            for variable in BINARY_SENSOR_TYPES:
                if BINARY_SENSOR_TYPES[variable][0] in [TYPE_ALL, TYPE_SMOKE_CO_ALARM]:
                    binary_sensors.append(
                        NestBinarySensor(structure, device, variable))

        for structure, device in nest.thermostats():
            for variable in BINARY_SENSOR_TYPES:
                if BINARY_SENSOR_TYPES[variable][0] in [TYPE_ALL, TYPE_THERMOSTAT]:
                    binary_sensors.append(
                        NestBinarySensor(structure, device, variable))

        return binary_sensors

    async_add_entities(await hass.async_add_job(get_binary_sensors), True)


class NestBinarySensor(BinarySensorEntity, NestDevice):
    """Representation of a Nest binary sensor."""

    def __init__(self, structure, device, variable):
        """Initialize the sensor."""
        super().__init__(structure, device)
        self.variable = variable
        if device:
            self._name = f"{self.device.name_long} {BINARY_SENSOR_TYPES[self.variable][1]}"
        else:
            self._name = f"{self.structure.name} Nest {BINARY_SENSOR_TYPES[self.variable][1]}"

        self._device_class = BINARY_SENSOR_TYPES[self.variable][2]
        self._state = None
        self._unique_id = f"{self.device.serial}-{self.variable}"

        if self.variable == "camera_status":
            self._motion_detected = None
            self._online = None
            self._person_detected = None
            self._sound_detected = None
            self._activity_zones = {}
            self._activity_detected = {}
            for zone in self.device.activity_zones:
                self._activity_zones[zone.zone_id] = zone.name.lower()
                self._activity_detected[zone.zone_id] = None

        if self.variable == "protect_status":
            self._battery_health = None
            self._co_status = None
            self._color_status = None
            self._online = None
            self._smoke_status = None

    @property
    def device_class(self):
        """Return the device class of the binary sensor."""
        return self._device_class

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = super().device_state_attributes

        if self.variable == "camera_status":
            attrs[ATTR_ONLINE] = self._online
            attrs[ATTR_MOTION_DETECTED] = self._motion_detected
            attrs[ATTR_PERSON_DETECTED] = self._person_detected
            attrs[ATTR_SOUND_DETECTED] = self._sound_detected
            for zone_id, zone_name in self._activity_zones.items():
                attrs[f"{zone_name}_{ATTR_ACTIVITY_DETECTED}"] = self._activity_detected[zone_id]

        if self.variable == "protect_status":
            attrs[ATTR_ONLINE] = self._online
            attrs[ATTR_COLOR_STATUS] = self._color_status
            attrs[ATTR_BATTERY_HEALTH] = self._battery_health
            attrs[ATTR_CO_STATUS] = self._co_status
            attrs[ATTR_SMOKE_STATUS] = self._smoke_status

        return attrs

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    def update(self):
        """Retrieve latest state."""
        if self.variable == "away":
            value = getattr(self.device, self.variable)
            self._state = bool(value == STATE_AWAY)

        elif self.variable == "battery_low":
            value = getattr(self.device, ATTR_BATTERY_HEALTH)
            self._state = not bool(value == STATE_OK)

        elif self.variable == "camera_status":
            self._motion_detected = getattr(self.device, ATTR_MOTION_DETECTED)
            self._online = getattr(self.device, ATTR_ONLINE)
            self._person_detected = getattr(self.device, ATTR_PERSON_DETECTED)
            self._sound_detected = getattr(self.device, ATTR_SOUND_DETECTED)
            for zone_id, zone_name in self._activity_zones.items():
                self._activity_detected[zone_id] = bool(self.device.has_ongoing_motion_in_zone(zone_id))
            self._state = any(
                [
                    bool(self._motion_detected),
                    bool(self._person_detected),
                    bool(self._sound_detected),
                    any(self._activity_detected.values()),
                ]
            )

        elif self.variable == "co_detected":
            value = getattr(self.device, ATTR_CO_STATUS)
            self._state = not bool(value == STATE_OK)

        elif self.variable == "protect_status":
            self._battery_health = getattr(self.device, ATTR_BATTERY_HEALTH)
            self._co_status = getattr(self.device, ATTR_CO_STATUS)
            self._color_status = getattr(self.device, ATTR_COLOR_STATUS)
            self._online = getattr(self.device, ATTR_ONLINE)
            self._smoke_status = getattr(self.device, ATTR_SMOKE_STATUS)
            self._state = any(
                [
                    not bool(self._color_status == STATE_GREEN),
                ]
            )

        elif self.variable == "security_state":
            value = getattr(self.device, self.variable)
            self._state = not bool(value == STATE_OK)

        elif self.variable == "smoke_detected":
            value = getattr(self.device, ATTR_SMOKE_STATUS)
            self._state = not bool(value == STATE_OK)

        else:
            self._state = bool(getattr(self.device, self.variable))


class NestActivityZoneSensor(NestBinarySensor):
    """Representation of a Nest binary sensor for activity in a zone."""

    def __init__(self, structure, device, variable, zone):
        """Initialize the sensor."""
        super().__init__(structure, device, variable)
        self._name = f"{self.device.name_long} {zone.name} Activity"
        self._unique_id = f"{self.device.serial}-{zone.zone_id}"
        self._zone = zone

    def update(self):
        """Retrieve latest state."""
        self._state = self.device.has_ongoing_motion_in_zone(self._zone.zone_id)

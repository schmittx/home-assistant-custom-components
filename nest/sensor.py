"""Custom Component"""

"""Support for Nest sensors."""
import logging
#import time

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_TIMESTAMP,
    PERCENTAGE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    TIME_MINUTES,
)
from homeassistant.helpers.entity import Entity
import homeassistant.util.temperature as temp_util

from . import NestDevice, NestWebClientDevice, supported_device
from .const import (
    DATA_CLIENT,
    DATA_COORDINATOR,
    DATA_NEST,
    DOMAIN as NEST_DOMAIN,
    MANUFACTURER,
    MODEL_TEMPERATURE_SENSOR,
    MODEL_THERMOSTAT,
    TYPE_ALL,
    TYPE_CAMERA,
    TYPE_SMOKE_CO_ALARM,
    TYPE_STRUCTURE,
    TYPE_TEMPERATURE_SENSOR,
    TYPE_THERMOSTAT,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "battery_health": [TYPE_SMOKE_CO_ALARM, "Battery Health", None, None, None],
    "co_status": [TYPE_SMOKE_CO_ALARM, "CO Status", None, None, None],
    "color_status": [TYPE_SMOKE_CO_ALARM, "Color Status", None, None, None],
    "eta_begin": [TYPE_STRUCTURE, "ETA", DEVICE_CLASS_TIMESTAMP, None, "mdi:calendar-clock"],
    "fan_timer": [TYPE_THERMOSTAT, "Fan Timer Duration", None, TIME_MINUTES, "mdi:timer-outline"],
    "fan_timeout": [TYPE_THERMOSTAT, "Fan Timer Timeout", DEVICE_CLASS_TIMESTAMP, None, "mdi:calendar-clock"],
    "humidity": [TYPE_THERMOSTAT, "Humidity", DEVICE_CLASS_HUMIDITY, PERCENTAGE, None],
    "hvac_state": [TYPE_THERMOSTAT, "HVAC State", None, None, None],
    "mode": [TYPE_THERMOSTAT, "Operation Mode", None, None, None],
    "security_state": [TYPE_STRUCTURE, "Security State", None, None, None],
    "smoke_status": [TYPE_SMOKE_CO_ALARM, "Smoke Status", None, None, None],
    "target": [TYPE_THERMOSTAT, "Target Temperature", DEVICE_CLASS_TEMPERATURE, None, None],
    "time_to_target": [TYPE_THERMOSTAT, "Time to Target", None, TIME_MINUTES, "mdi:clock-outline"],
    "temperature": [TYPE_THERMOSTAT, "Current Temperature", DEVICE_CLASS_TEMPERATURE, None, None],
}

ADDITIONAL_SENSOR_TYPES = {
    "backplate_temperature": [TYPE_THERMOSTAT, "Temperature", DEVICE_CLASS_TEMPERATURE, None, None],
    "battery_level": [TYPE_TEMPERATURE_SENSOR, "Temperature Sensor Battery", DEVICE_CLASS_BATTERY, None, None],
    "current_temperature": [TYPE_TEMPERATURE_SENSOR, "Temperature", DEVICE_CLASS_TEMPERATURE, None, None],
    "target_humidity": [TYPE_THERMOSTAT, "Thermostat Target Humidity", DEVICE_CLASS_HUMIDITY, PERCENTAGE, None],
    "temp_c": [TYPE_STRUCTURE, "Outdoor Temperature", DEVICE_CLASS_TEMPERATURE, None, None],
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Nest Sensor.

    No longer used.
    """


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up a Nest sensor based on a config entry."""
    nest = hass.data[NEST_DOMAIN][DATA_NEST]
    client = hass.data[NEST_DOMAIN].get(DATA_CLIENT)
    coordinator = hass.data[NEST_DOMAIN].get(DATA_COORDINATOR)
    unit = hass.config.units.temperature_unit

    def get_sensors():
        """Get the Nest sensors."""
        sensors = []

        for structure in nest.structures():
            for variable in SENSOR_TYPES:
                if SENSOR_TYPES[variable][0] == TYPE_STRUCTURE:
                    sensors.append(NestSensor(structure, None, variable))

            if supported_device(client, structure):
                id = client.get_device_id(structure.name)
                for variable in ADDITIONAL_SENSOR_TYPES:
                    if ADDITIONAL_SENSOR_TYPES[variable][0] in [TYPE_ALL, TYPE_STRUCTURE]:
                        sensors.append(NestAdditionalSensor(structure, None, variable, unit, client, coordinator, id))

        for structure, device in nest.cameras():
            for variable in SENSOR_TYPES:
                if SENSOR_TYPES[variable][0] == TYPE_CAMERA:
                    sensors.append(NestSensor(structure, device, variable))

        for structure, device in nest.smoke_co_alarms():
            for variable in SENSOR_TYPES:
                if SENSOR_TYPES[variable][0] == TYPE_SMOKE_CO_ALARM:
                    sensors.append(NestSensor(structure, device, variable))

        for structure, device in nest.thermostats():
            for variable in SENSOR_TYPES:
                if SENSOR_TYPES[variable][0] == TYPE_THERMOSTAT:
                    sensors.append(NestSensor(structure, device, variable))

            if supported_device(client, device):
                id = client.get_device_id(device.name_long)
                for variable in ADDITIONAL_SENSOR_TYPES:
                    if ADDITIONAL_SENSOR_TYPES[variable][0] in [TYPE_ALL, TYPE_THERMOSTAT]:
                        sensors.append(NestAdditionalSensor(structure, device, variable, unit, client, coordinator, id))
                for sensor in client.temperature_sensors:
                    for variable in ADDITIONAL_SENSOR_TYPES:
                        if ADDITIONAL_SENSOR_TYPES[variable][0] in [TYPE_ALL, TYPE_TEMPERATURE_SENSOR]:
                            sensors.append(NestAdditionalSensor(structure, device, variable, unit, client, coordinator, sensor))

        return sensors

    async_add_entities(await hass.async_add_job(get_sensors), True)


class NestSensor(NestDevice):
    """Representation of a Nest sensor."""

    def __init__(self, structure, device, variable):
        """Initialize the sensor."""
        super().__init__(structure, device)
        self.variable = variable
        if device:
            self._name = f"{self.device.name_long} {SENSOR_TYPES[self.variable][1]}"
        else:
            self._name = f"{self.structure.name} Nest {SENSOR_TYPES[self.variable][1]}"

        self._device_class = SENSOR_TYPES[self.variable][2]
        self._icon = SENSOR_TYPES[self.variable][4]
        self._state = None
        self._unique_id = f"{self.device.serial}-{self.variable}"
        self._unit = SENSOR_TYPES[variable][3]

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit

    def update(self):
        """Retrieve latest state."""
        state = getattr(self.device, self.variable)

        if state is None:
            self._state = None

        if SENSOR_TYPES[self.variable][2] == DEVICE_CLASS_TEMPERATURE:
            if isinstance(state, tuple):
                low, high = state
                state = f"{int(low)}-{int(high)}"
            else:
                state = round(state, 1)

            if self.device.temperature_scale == "C":
                self._unit = TEMP_CELSIUS
            else:
                self._unit = TEMP_FAHRENHEIT

        self._state = state


class NestAdditionalSensor(NestWebClientDevice):
    """Representation of a Nest sensor."""

    def __init__(self, structure, device, variable, unit, client, coordinator, id):
        """Initialize the sensor."""
        super().__init__(structure, device, client, coordinator, id)
        self.variable = variable

        if device:
            location = self.coordinator.data[self.id].get("location")
            self._name = f"{location} {ADDITIONAL_SENSOR_TYPES[self.variable][1]}"
        else:
            self._name = f"{structure.name} {ADDITIONAL_SENSOR_TYPES[self.variable][1]}"

        self._device_class = ADDITIONAL_SENSOR_TYPES[self.variable][2]
        self._icon = ADDITIONAL_SENSOR_TYPES[self.variable][4]
        self._unique_id = f"{self.id}-{self.variable}"
        if ADDITIONAL_SENSOR_TYPES[self.variable][2] == DEVICE_CLASS_TEMPERATURE:
            self._unit = unit
        else:
            self._unit = ADDITIONAL_SENSOR_TYPES[variable][3]

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit

    @property
    def _battery_level(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self.id].get("battery_level")

    @property
    def _state(self):
        """Return the state of the sensor."""
        state = self.coordinator.data[self.id].get(self.variable)
        if ADDITIONAL_SENSOR_TYPES[self.variable][2] == DEVICE_CLASS_TEMPERATURE and self._unit == TEMP_FAHRENHEIT:
            return round(temp_util.convert(state, TEMP_CELSIUS, TEMP_FAHRENHEIT))
        return state

    @property
    def device_info(self):
        """Return information about the device."""
        if ADDITIONAL_SENSOR_TYPES[self.variable][0] == TYPE_TEMPERATURE_SENSOR:
            device_info = {
                "identifiers": {(NEST_DOMAIN, self.id)},
                "name": self.coordinator.data[self.id].get("name"),
                "manufacturer": MANUFACTURER,
                "model": MODEL_TEMPERATURE_SENSOR,
                "via_device": (NEST_DOMAIN, self.device.device_id),
            }
        else:
            device_info = super().device_info
        return device_info

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = super().device_state_attributes
        if ADDITIONAL_SENSOR_TYPES[self.variable][0] == TYPE_TEMPERATURE_SENSOR and self._battery_level is not None:
            attrs[ATTR_BATTERY_LEVEL] = self._battery_level
#        if self.variable == "temp_c":
#            sunrise = self.coordinator.data[self.id].get("sunrise")
#            sunset = self.coordinator.data[self.id].get("sunset")
#            attrs["sunrise"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sunrise))
#            attrs["sunset"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sunset))
        return attrs

"""Support for system monitor sensors."""
import logging
import os
#import platform

import psutil

from homeassistant.const import (
    CONF_TYPE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify
import homeassistant.util.dt as dt_util

from .const import (
    CONF_ARG,
    CPU_SENSOR_PREFIXES,
    DOMAIN,
    IF_ADDRS_FAMILY,
    IO_COUNTER,
    SENSOR_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up a system monitor sensor based on a config entry."""
    type = entry.data[CONF_TYPE]
    arg = entry.data.get(CONF_ARG)

    # Initialize the sensor argument if none was provided.
    # For disk monitoring default to "/" (root) to prevent runtime errors, if argument was not specified.
    if type.startswith("disk_") and arg is None:
        arg = "/"

    # Verify if we can retrieve CPU / processor temperatures.
    # If not, do not create the entity and add a warning to the log
    if type == "processor_temperature":
        if SystemMonitorSensor.read_cpu_temperature() is None:
            _LOGGER.warning("Cannot read CPU / processor temperature information.")
            return


    async_add_entities([SystemMonitorSensor(type, arg)], True)


class SystemMonitorSensor(Entity):
    """Implementation of a system monitor sensor."""

    def __init__(self, sensor_type, argument=None):
        """Initialize the sensor."""
        self.argument = argument
        self.type = sensor_type

        self._name = SENSOR_TYPES[self.type][0]
        self._unique_id = slugify(self.type)
        if self.argument:
            self._name = f"{self._name} {self.argument}"
            self._unique_id = slugify(f"{self._unique_id}_{self.argument}")
        self._state = None
        self._unit_of_measurement = SENSOR_TYPES[self.type][1]
        self._available = True
        if self.type in ["throughput_network_out", "throughput_network_in"]:
            self._last_value = None
            self._last_update_time = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name.rstrip()

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return SENSOR_TYPES[self.type][3]

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return SENSOR_TYPES[self.type][2]

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    def update(self):
        """Get the latest system information."""
        if self.type == "disk_use_percent":
            self._state = psutil.disk_usage(self.argument).percent
        elif self.type == "disk_use":
            self._state = round(psutil.disk_usage(self.argument).used / 1024 ** 3, 1)
        elif self.type == "disk_free":
            self._state = round(psutil.disk_usage(self.argument).free / 1024 ** 3, 1)
        elif self.type == "memory_use_percent":
            self._state = psutil.virtual_memory().percent
        elif self.type == "memory_use":
            virtual_memory = psutil.virtual_memory()
            self._state = round(
                (virtual_memory.total - virtual_memory.available) / 1024 ** 2, 1
            )
        elif self.type == "memory_free":
            self._state = round(psutil.virtual_memory().available / 1024 ** 2, 1)
        elif self.type == "swap_use_percent":
            self._state = psutil.swap_memory().percent
        elif self.type == "swap_use":
            self._state = round(psutil.swap_memory().used / 1024 ** 2, 1)
        elif self.type == "swap_free":
            self._state = round(psutil.swap_memory().free / 1024 ** 2, 1)
        elif self.type == "processor_use":
            self._state = round(psutil.cpu_percent(interval=None))
        elif self.type == "processor_temperature":
            self._state = self.read_cpu_temperature()
        elif self.type == "process":
            for proc in psutil.process_iter():
                try:
                    if self.argument == proc.name():
                        self._state = STATE_ON
                        return
                except psutil.NoSuchProcess as err:
                    _LOGGER.warning(
                        "Failed to load process with id: %s, old name: %s",
                        err.pid,
                        err.name,
                    )
            self._state = STATE_OFF
        elif self.type == "network_out" or self.type == "network_in":
            counters = psutil.net_io_counters(pernic=True)
            if self.argument in counters:
                counter = counters[self.argument][IO_COUNTER[self.type]]
                self._state = round(counter / 1024 ** 2, 1)
            else:
                self._state = None
        elif self.type == "packets_out" or self.type == "packets_in":
            counters = psutil.net_io_counters(pernic=True)
            if self.argument in counters:
                self._state = counters[self.argument][IO_COUNTER[self.type]]
            else:
                self._state = None
        elif (
            self.type == "throughput_network_out"
            or self.type == "throughput_network_in"
        ):
            counters = psutil.net_io_counters(pernic=True)
            if self.argument in counters:
                counter = counters[self.argument][IO_COUNTER[self.type]]
                now = dt_util.utcnow()
                if self._last_value and self._last_value < counter:
                    self._state = round(
                        (counter - self._last_value)
                        / 1000 ** 2
                        / (now - self._last_update_time).seconds,
                        3,
                    )
                else:
                    self._state = None
                self._last_update_time = now
                self._last_value = counter
            else:
                self._state = None
        elif self.type == "ipv4_address" or self.type == "ipv6_address":
            addresses = psutil.net_if_addrs()
            if self.argument in addresses:
                for addr in addresses[self.argument]:
                    if addr.family == IF_ADDRS_FAMILY[self.type]:
                        self._state = addr.address
            else:
                self._state = None
        elif self.type == "last_boot":
            self._state = dt_util.as_local(
                dt_util.utc_from_timestamp(psutil.boot_time())
            ).isoformat()
        elif self.type == "load_1m":
            self._state = round(os.getloadavg()[0], 2)
        elif self.type == "load_5m":
            self._state = round(os.getloadavg()[1], 2)
        elif self.type == "load_15m":
            self._state = round(os.getloadavg()[2], 2)

    @staticmethod
    def read_cpu_temperature():
        """Attempt to read CPU / processor temperature."""
        temps = psutil.sensors_temperatures()

        for name, entries in temps.items():
            i = 1
            for entry in entries:
                # In case the label is empty (e.g. on Raspberry PI 4),
                # construct it ourself here based on the sensor key name.
                if not entry.label:
                    _label = f"{name} {i}"
                else:
                    _label = entry.label

                if _label in CPU_SENSOR_PREFIXES:
                    return round(entry.current, 1)

                i += 1

#    @property
#    def device_info(self):
#        """Return information about the device."""
#        info = platform.uname()
#        device_info = {
#            "identifiers": {(DOMAIN, platform.platform(terse=True))},
#            "name": info.node,
#            "manufacturer": info.system,
#            "model": info.machine,
#            "sw_version": info.version,
#        }
#        return device_info

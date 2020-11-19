"""Custom Component"""

"""Interfaces with TotalConnect sensors."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_SOUND,
    DEVICE_CLASS_WINDOW,
)
from homeassistant.const import ATTR_ATTRIBUTION

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

ZONE_INFO = {
    1: {"alias": "Smoke Detector", "model": "2W-B"},
    2: {"alias": "Glass Break Sensor", "model": "FG1625F"},
    3: {"alias": None, "model": "944TSP"},
    4: {"alias": None, "model": "944TSP"},
    5: {"alias": None, "model": "944TSP"},
    9: {"alias": None, "model": "944TSP"},
    10: {"alias": None, "model": "944TSP"},
    11: {"alias": None, "model": "944TSP"},
    12: {"alias": None, "model": "944TSP"},
    13: {"alias": None, "model": "944TSP"},
    17: {"alias": None, "model": "5820L"},
    18: {"alias": None, "model": "5820L"},
    19: {"alias": None, "model": "5820L"},
    20: {"alias": None, "model": "5820L"},
}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up TotalConnect device sensors based on a config entry."""
    sensors = []

    client_locations = hass.data[DOMAIN][entry.entry_id].locations

    for location_id, location in client_locations.items():
        for zone_id, zone in location.zones.items():
            sensors.append(TotalConnectBinarySensor(location_id, zone_id, zone))

    async_add_entities(sensors, True)


class TotalConnectBinarySensor(BinarySensorEntity):
    """Represent an TotalConnect zone."""

    def __init__(self, location_id, zone_id, zone):
        """Initialize the TotalConnect status."""
        self._is_bypassed = None
        self._is_faulted = None
        self._is_low_battery = None
        self._is_on = None
        self._is_tampered = None
        self._is_triggered = None
        self._location_id = location_id
        self._zone = zone
        self._zone_id = zone_id

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self._location_id}-{self._zone_id}"

    @property
    def name(self):
        """Return the name of the device."""
        return self._zone.description.title().replace("'S", "’s")

    @property
    def device_info(self):
        """Return the device_info of the device."""
        name = ZONE_INFO[self._zone_id]["alias"]
        if not name:
            name = f"{self.name} Contact Sensor"
        device_info = {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": name,
            "manufacturer": MANUFACTURER,
            "model": ZONE_INFO[self._zone_id]["model"],
#            "sw_version": "Unknown",
            "via_device": (DOMAIN, self._location_id),
        }
        return device_info

    def update(self):
        """Return the state of the device."""
        self._is_bypassed = self._zone.is_bypassed()
        self._is_faulted = self._zone.is_faulted()
        self._is_low_battery = self._zone.is_low_battery()
        self._is_tampered = self._zone.is_tampered()
        self._is_triggered = self._zone.is_triggered()

        if self._zone.is_faulted() or self._zone.is_triggered():
            self._is_on = True
        else:
            self._is_on = False

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        if self._zone.is_type_fire():
            return DEVICE_CLASS_SMOKE
        if self._zone.is_type_carbon_monoxide():
            return DEVICE_CLASS_GAS
        if "window" in self.name.lower():
            return DEVICE_CLASS_WINDOW
        if "door" in self.name.lower():
            return DEVICE_CLASS_DOOR
        if "glass break" in self.name.lower():
            return DEVICE_CLASS_SOUND
        return DEVICE_CLASS_PROBLEM

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "bypassed": self._is_bypassed,
            "faulted": self._is_faulted,
            "location_id": self._location_id,
            "low_battery": self._is_low_battery,
            "tampered": self._is_tampered,
            "triggered": self._is_triggered,
            "zone_id": self._zone_id,
            "zone_type": self._zone.zone_type_id,
        }
        return attrs

"""Support for Eero sensors."""
import logging

from . import EeroEntity
from .const import (
    CONF_CLIENTS,
    CONF_EEROS,
    CONF_NETWORK,
    CONF_PROFILES,
    DATA_COORDINATOR,
    DOMAIN as EERO_DOMAIN,
    TYPE_CLIENT,
    TYPE_EERO,
    TYPE_NETWORK,
    TYPE_PROFILE,
)

_LOGGER = logging.getLogger(__name__)

BASIC_TYPES = {
    "connected_clients_count": [[TYPE_EERO], "Connected Clients", None, None, "clients"],
    "public_ip": [[TYPE_NETWORK], "Public IP", None, None, None],
    "speed_down": [[TYPE_NETWORK], "Download Speed", None, None, None],
    "speed_up": [[TYPE_NETWORK], "Upload Speed", None, None, None],
    "status": [[TYPE_EERO, TYPE_NETWORK], "Status", None, None, None],
}

SENSOR_TYPES = {**BASIC_TYPES}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up a Eero sensor based on a config entry."""
    conf = hass.data[EERO_DOMAIN][entry.entry_id]
    conf_network = conf[CONF_NETWORK]
    conf_eeros = conf[CONF_EEROS]
    conf_profiles = conf[CONF_PROFILES]
    conf_clients = conf[CONF_CLIENTS]
    coordinator = conf[DATA_COORDINATOR]

    def get_sensors():
        """Get the Eero sensors."""
        sensors = []

        for variable in SENSOR_TYPES:
            if TYPE_NETWORK in SENSOR_TYPES[variable][0]:
                sensors.append(EeroSensor(coordinator, conf_network.id, None, variable))

        for eero in conf_eeros:
            for variable in SENSOR_TYPES:
                if TYPE_EERO in SENSOR_TYPES[variable][0]:
                    sensors.append(EeroSensor(coordinator, conf_network.id, eero.id, variable))

        for profile in conf_profiles:
            for variable in SENSOR_TYPES:
                if TYPE_PROFILE in SENSOR_TYPES[variable][0]:
                    sensors.append(EeroSensor(coordinator, conf_network.id, profile.id, variable))

        for client in conf_clients:
            for variable in SENSOR_TYPES:
                if TYPE_CLIENT in SENSOR_TYPES[variable][0]:
                    sensors.append(EeroSensor(coordinator, conf_network.id, client.id, variable))

        return sensors

    async_add_entities(await hass.async_add_job(get_sensors), True)


class EeroSensor(EeroEntity):
    """Representation of a Eero sensor."""

    @property
    def name(self):
        """Return the name of the entity."""
        if self.resource.is_client:
            return f"{self.network.name} {self.resource.name_connection_type} {SENSOR_TYPES[self.variable][1]}"
        elif self.resource.is_eero:
            return f"{self.network.name} {self.resource.name} Eero {SENSOR_TYPES[self.variable][1]}"
        return f"{self.resource.name} {SENSOR_TYPES[self.variable][1]}"

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SENSOR_TYPES[self.variable][2]

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return SENSOR_TYPES[self.variable][3]

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.variable in ["speed_up", "speed_down"]:
            speed = self.resource.speed
            return round(speed[0]) if self.variable == "speed_down" else round(speed[1])
        return getattr(self.resource, self.variable)

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self.variable in ["speed_up", "speed_down"]:
            speed_units = self.resource.speed_units
            return speed_units[0] if self.variable == "speed_down" else speed_units[1]
        return SENSOR_TYPES[self.variable][4]

    @property
    def device_state_attributes(self):
        attrs = super().device_state_attributes
        if self.variable in ["speed_up", "speed_down"]:
            attrs["last_updated"] = self.resource.speed_date
        elif self.variable == "status" and self.resource.is_network:
            for attr in ["health_eero_network_status", "health_internet_isp_up", "health_internet_status"]:
                attrs[attr] = getattr(self.resource, attr)
        return attrs

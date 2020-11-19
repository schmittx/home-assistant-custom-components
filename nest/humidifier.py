"""Custom Component"""

"""Support for Nest thermostats."""
import logging

from homeassistant.components.climate.const import ATTR_CURRENT_HUMIDITY
from homeassistant.components.humidifier import (
    DEVICE_CLASS_HUMIDIFIER,
    SUPPORT_MODES,
    HumidifierEntity,
)
from homeassistant.const import STATE_IDLE

from . import NestWebClientDevice, supported_device
from .climate import NEST_MODE_OFF
from .const import (
    ATTR_HUMIDIFIER_ACTION,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DATA_NEST,
    DOMAIN as NEST_DOMAIN,
    NEST_HUMIDITY_MAX,
    NEST_HUMIDITY_MIN,
    NEST_HUMIDITY_STEP,
    STATE_AUTO,
    STATE_HUMIDIFYING,
)

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Nest thermostat.

    No longer in use.
    """


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Nest humidifier device based on a config entry."""
    nest = hass.data[NEST_DOMAIN][DATA_NEST]
    client = hass.data[NEST_DOMAIN].get(DATA_CLIENT)
    coordinator = hass.data[NEST_DOMAIN].get(DATA_COORDINATOR)

    def get_humidifiers():
        """Get the Nest humidifiers."""
        humidifiers = []

        for structure, device in nest.thermostats():
            if supported_device(client, device):
                id = client.get_device_id(device.name_long)
                if bool(coordinator.data[id]["has_humidifier"]):
                    humidifiers.append(NestHumidifier(structure, device, client, coordinator, id))

        return humidifiers

    all_humidifiers = await hass.async_add_job(get_humidifiers)

    async_add_entities(all_humidifiers, True)


class NestHumidifier(HumidifierEntity, NestWebClientDevice):
    """Representation of a Nest thermostat."""

    def __init__(self, structure, device, client, coordinator, id):
        """Initialize the thermostat."""
        super().__init__(structure, device, client, coordinator, id)

        self._name = self.structure.name
        self._unique_id = f"{self.device.device_id}-humidifier"

        self._support_flags = SUPPORT_MODES

        self._current_humidity = None
        self._mode = None

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def is_on(self):
        """Return true if the humidifier is on."""
        return self._target_humidity_enabled and self._mode != NEST_MODE_OFF

    @property
    def device_class(self):
        """Return the device class of the humidifier."""
        return DEVICE_CLASS_HUMIDIFIER

    @property
    def min_humidity(self):
        """Return the minimum humidity."""
        return NEST_HUMIDITY_MIN

    @property
    def max_humidity(self):
        """Return the maximum humidity."""
        return NEST_HUMIDITY_MAX

    @property
    def target_humidity(self):
        """Return the humidity we try to reach."""
        return self._target_humidity

    @property
    def mode(self):
        """Return the current mode, e.g., home, auto, baby.

        Requires SUPPORT_MODES.
        """
        return STATE_AUTO

    @property
    def available_modes(self):
        """Return a list of available modes.

        Requires SUPPORT_MODES.
        """
        return [STATE_AUTO]

    @property
    def state_attributes(self):
        attrs = {**super().state_attributes, **super().device_state_attributes}
        if self._current_humidity is not None:
            attrs[ATTR_CURRENT_HUMIDITY] = self._current_humidity
        if self._humidifier_state is not None:
            attrs[ATTR_HUMIDIFIER_ACTION] = self._humidifier_state
        return attrs

    def turn_on(self):
        """Turn the entity on."""
        self.client.thermostat_enable_target_humidity(self.id, True)

    def turn_off(self):
        """Turn the entity off."""
        self.client.thermostat_enable_target_humidity(self.id, False)

    def set_mode(self, mode):
        """Set new mode."""
        self.client.thermostat_enable_target_humidity(self.id, mode == STATE_AUTO)

    def set_humidity(self, humidity):
        """Set new target humidity."""
        humidity = int(round(float(humidity) / NEST_HUMIDITY_STEP) * NEST_HUMIDITY_STEP)
        if humidity < NEST_HUMIDITY_MIN:
            humidity = NEST_HUMIDITY_MIN
        if humidity > NEST_HUMIDITY_MAX:
            humidity = NEST_HUMIDITY_MAX
        self.client.thermostat_set_target_humidity(self.id, humidity)

    @property
    def _target_humidity_enabled(self):
        """Return the minimum humidity."""
        return bool(self.coordinator.data[self.id].get("target_humidity_enabled"))

    @property
    def _humidifier_state(self):
        """Return the minimum humidity."""
        humidifier_state = bool(self.coordinator.data[self.id].get("humidifier_state"))
        return STATE_HUMIDIFYING if humidifier_state else STATE_IDLE

    @property
    def _target_humidity(self):
        """Return the minimum humidity."""
        return self.coordinator.data[self.id].get("target_humidity")

    def update(self):
        """Cache value from Python-nest."""
        self._current_humidity = self.device.humidity
        self._mode = self.device.mode

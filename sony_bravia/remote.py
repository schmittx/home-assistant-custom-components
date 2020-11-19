"""Remote control support for Sony TV."""
import logging

from homeassistant.components.remote import RemoteEntity, DOMAIN as DOMAIN_REMOTE

from . import SonyBRAVIABase
from .const import (
    ATTR_COMMAND_LIST,
    BRAVIA_CLIENT,
    BRAVIA_COORDINATOR,
    DOMAIN,
    STATE_ACTIVE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Nest device sensors based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]

    client = data.get(BRAVIA_CLIENT)
    coordinator = data.get(BRAVIA_COORDINATOR)

    async_add_entities([SonyBRAVIARemote(client, coordinator)], True)


class SonyBRAVIARemote(RemoteEntity, SonyBRAVIABase):
    """Device that sends commands to a Sony TV."""

    def __init__(self, client, coordinator):
        """Initialize device."""
        super().__init__(client, coordinator)

        self._unique_id = f"{self._cid}-{DOMAIN_REMOTE}"

    @property
    def _commands(self):
        """Name of the current running app."""
        return self.coordinator.data.get("commands", {})

    @property
    def _is_on(self):
        """Name of the current running app."""
        return self.coordinator.data.get("power_status") == STATE_ACTIVE

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._is_on

    @property
    def state_attributes(self):
        """Return the state attributes."""
        attrs = super().state_attributes

        if not attrs:
            attrs = {}

        if self._is_on and self._commands:
            attrs[ATTR_COMMAND_LIST] = sorted(self._commands.keys())

        return attrs

#    async def async_send_command(self, command, **kwargs):
#        """Send commands to a device."""
#        if self._is_on:
#            for _command in command:
#                if _command in self._commands:
#                    await self.hass.async_add_job(self.client.send_command, self._commands[_command])
#                    await self.coordinator.async_request_refresh()

    def send_command(self, command):
        """Send commands to a device."""
        for _command in command:
            if _command in self._commands:
                self.client.send_command(self._commands[_command])

#    async def async_turn_on(self, **kwargs):
#        """Turn the entity on."""
#        await self.hass.async_add_job(self.client.set_power_status, True)
#        await self.coordinator.async_request_refresh()

    def turn_on(self, **kwargs):
        """Turn the entity on."""
        self.client.set_power_status(True)

#    async def async_turn_off(self, **kwargs):
#        """Turn the media player off."""
#        await self.hass.async_add_job(self.client.set_power_status, False)
#        await self.coordinator.async_request_refresh()

    def turn_off(self, **kwargs):
        """Turn the entity off."""
        self.client.set_power_status(False)

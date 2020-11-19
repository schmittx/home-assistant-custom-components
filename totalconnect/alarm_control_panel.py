"""Custom Component"""

"""Interfaces with TotalConnect alarm control panels."""
import logging

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_NIGHT,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_DISARMING,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.exceptions import HomeAssistantError

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up TotalConnect alarm panels based on a config entry."""
    alarms = []

    client = hass.data[DOMAIN][entry.entry_id]

    for location_id, location in client.locations.items():
        location_name = location.location_name
        alarms.append(TotalConnectAlarm(location_name, location_id, client))

    async_add_entities(alarms, True)


class TotalConnectAlarm(alarm.AlarmControlPanelEntity):
    """Represent an TotalConnect status."""

    def __init__(self, name, location_id, client):
        """Initialize the TotalConnect status."""
        self._name = name
        self._location_id = location_id
        self._client = client
        self._state = None
        self._device_state_attributes = {}

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_NIGHT

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._device_state_attributes

    @property
    def code_arm_required(self):
        """Whether the code is required for arm actions."""
        return False

    @property
    def unique_id(self):
         """Return a unique, HASS-friendly identifier for this entity."""
         return self._location_id

    @property
    def device_info(self):
        """Return the device_info of the device."""
        device_info = {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": "Security Panel",
            "manufacturer": MANUFACTURER,
            "model": "VISTA-21iP",
#            "sw_version": "Unknown",
        }
        return device_info

    def update(self):
        """Return the state of the device."""
        self._client.get_armed_status(self._location_id)
        attrs = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "location_name": self._name,
            "location_id": self._location_id,
            "ac_loss": self._client.locations[self._location_id].ac_loss,
            "low_battery": self._client.locations[self._location_id].low_battery,
            "cover_tampered": self._client.locations[self._location_id].is_cover_tampered(),
            "faulted_zones": None,
            "tampered_zones": None,
            "triggered_source": None,
            "triggered_zones": None,
        }

        if self._client.locations[self._location_id].is_disarmed():
            state = STATE_ALARM_DISARMED
        elif self._client.locations[self._location_id].is_armed_home():
            state = STATE_ALARM_ARMED_HOME
        elif self._client.locations[self._location_id].is_armed_night():
            state = STATE_ALARM_ARMED_NIGHT
        elif self._client.locations[self._location_id].is_armed_away():
            state = STATE_ALARM_ARMED_AWAY
        elif self._client.locations[self._location_id].is_armed_custom_bypass():
            state = STATE_ALARM_ARMED_CUSTOM_BYPASS
        elif self._client.locations[self._location_id].is_arming():
            state = STATE_ALARM_ARMING
        elif self._client.locations[self._location_id].is_disarming():
            state = STATE_ALARM_DISARMING
        elif self._client.locations[self._location_id].is_triggered_police():
            state = STATE_ALARM_TRIGGERED
            attr["triggered_source"] = "Police/Medical"
        elif self._client.locations[self._location_id].is_triggered_fire():
            state = STATE_ALARM_TRIGGERED
            attr["triggered_source"] = "Fire/Smoke"
        elif self._client.locations[self._location_id].is_triggered_gas():
            state = STATE_ALARM_TRIGGERED
            attr["triggered_source"] = "Carbon Monoxide"
        else:
            logging.info("Total Connect Client returned unknown status")
            state = None

        faulted_zones = []
        tampered_zones = []
        triggered_zones = []
        for zone_id, zone in self._client.locations[self._location_id].zones.items():
            if zone.is_faulted():
                faulted_zones.append(zone.description.title())
            if zone.is_tampered():
                tampered_zones.append(zone.description.title())
            if zone.is_triggered():
                triggered_zones.append(zone.description.title())

        if faulted_zones:
            attrs["faulted_zones"] = faulted_zones
        if tampered_zones:
            attrs["tampered_zones"] = tampered_zones
        if triggered_zones:
            attrs["triggered_zones"] = triggered_zones

        self._state = state
        self._device_state_attributes = attrs

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        if self._client.disarm(self._location_id) is not True:
            raise HomeAssistantError(f"TotalConnect failed to disarm {self._name}.")

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        if self._client.arm_stay(self._location_id) is not True:
            raise HomeAssistantError(f"TotalConnect failed to arm home {self._name}.")

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        if self._client.arm_away(self._location_id) is not True:
            raise HomeAssistantError(f"TotalConnect failed to arm away {self._name}.")

    def alarm_arm_night(self, code=None):
        """Send arm night command."""
        if self._client.arm_stay_night(self._location_id) is not True:
            raise HomeAssistantError(f"TotalConnect failed to arm night {self._name}.")

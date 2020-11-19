"""Custom Component"""

"""Support for Nest thermostats."""
import logging

from nest.nest import APIError
import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    DOMAIN,
    FAN_AUTO,
    FAN_ON,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_NONE,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_HUMIDITY,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    STATE_IDLE,
    STATE_OFF,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from . import NestDevice, supported_device
from .const import (
    ATTR_DURATION,
    ATTR_ECO_MODE,
    ATTR_STRUCTURE,
    ATTR_TEMPERATURE_SCALE,
    ATTR_THERMOSTAT_TEMPERATURE,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DATA_NEST,
    DOMAIN as NEST_DOMAIN,
    NEST_HUMIDITY_MAX,
    NEST_HUMIDITY_MIN,
    NEST_HUMIDITY_STEP,
    PRESET_AWAY_AND_ECO,
    SERVICE_SET_ECO_MODE,
    SERVICE_SET_FAN_TIMER,
    SERVICE_SET_TEMPERATURE_SCALE,
    STATE_AUTO,
    STATE_AWAY,
    TEMP_SCALE_C,
    TEMP_SCALE_F,
)

_LOGGER = logging.getLogger(__name__)

ECO_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ECO_MODE): cv.boolean,
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)

FAN_TIMER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DURATION): vol.All(vol.Coerce(int), vol.In([15, 30, 45, 60, 120, 240, 480, 720])),
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)

TEMPERATURE_SCALE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TEMPERATURE_SCALE): vol.In([TEMP_SCALE_C, TEMP_SCALE_F]),
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)

TEMP_UNIT_MAP = {
    TEMP_SCALE_C: TEMP_CELSIUS,
    TEMP_SCALE_F: TEMP_FAHRENHEIT,
}

NEST_MODE_HEAT_COOL = "heat-cool"
NEST_MODE_ECO = "eco"
NEST_MODE_HEAT = "heat"
NEST_MODE_COOL = "cool"
NEST_MODE_OFF = "off"

MODE_HASS_TO_NEST = {
    HVAC_MODE_AUTO: NEST_MODE_HEAT_COOL,
    HVAC_MODE_HEAT: NEST_MODE_HEAT,
    HVAC_MODE_COOL: NEST_MODE_COOL,
    HVAC_MODE_OFF: NEST_MODE_OFF,
}

MODE_NEST_TO_HASS = {v: k for k, v in MODE_HASS_TO_NEST.items()}

ACTION_NEST_TO_HASS = {
    "off": CURRENT_HVAC_IDLE,
    "heating": CURRENT_HVAC_HEAT,
    "cooling": CURRENT_HVAC_COOL,
}

PRESET_MODES = [PRESET_NONE, PRESET_AWAY, PRESET_ECO, PRESET_AWAY_AND_ECO]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Nest thermostat.

    No longer in use.
    """


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Nest climate device based on a config entry."""
    nest = hass.data[NEST_DOMAIN][DATA_NEST]
    temp_unit = hass.config.units.temperature_unit
    client = hass.data[NEST_DOMAIN].get(DATA_CLIENT)
    coordinator = hass.data[NEST_DOMAIN].get(DATA_COORDINATOR)

    def get_thermostats():
        """Get the Nest thermostats."""
        thermostats = []

        for structure, device in nest.thermostats():
            if supported_device(client, device):
                id = client.get_device_id(device.name_long)
                if bool(coordinator.data[id]["has_dehumidifier"]) or bool(coordinator.data[id]["has_humidifier"]):
                    thermostats.append(NestThermostatHumidistat(structure, device, temp_unit, client, coordinator, id))
            else:
                thermostats.append(NestThermostat(structure, device, temp_unit))

        return thermostats

    all_thermostats = await hass.async_add_job(get_thermostats)

    if all_thermostats:
        def validate_thermostats(target_thermostats):
            validated_thermostats = []
            if target_thermostats:
                for device in all_thermostats:
                    if device.entity_id in target_thermostats:
                        validated_thermostats.append(device)
            else:
                validated_thermostats = all_thermostats
            return validated_thermostats

        def set_eco_mode(service):
            """
            Set the Eco mode for a Nest thermostat.
            """
            entity_id = service.data.get(ATTR_ENTITY_ID)
            for thermostat in validate_thermostats(entity_id):
                thermostat.set_eco_mode(
                    service.data[ATTR_ECO_MODE])

        def set_fan_timer(service):
            """
            Set the fan timer for a Nest thermostat.
            """
            entity_id = service.data.get(ATTR_ENTITY_ID)
            for thermostat in validate_thermostats(entity_id):
                thermostat.set_fan_timer(
                    service.data[ATTR_DURATION])

        def set_temperature_scale(service):
            """
            Set the temperature scale for a Nest thermostat.
            """
            entity_id = service.data.get(ATTR_ENTITY_ID)
            for thermostat in validate_thermostats(entity_id):
                thermostat.set_temperature_scale(
                    service.data[ATTR_TEMPERATURE_SCALE])

        hass.services.async_register(
            NEST_DOMAIN,
            SERVICE_SET_ECO_MODE,
            set_eco_mode,
            schema=ECO_MODE_SCHEMA,
        )

        hass.services.async_register(
            NEST_DOMAIN,
            SERVICE_SET_FAN_TIMER,
            set_fan_timer,
            schema=FAN_TIMER_SCHEMA,
        )

        hass.services.async_register(
            NEST_DOMAIN,
            SERVICE_SET_TEMPERATURE_SCALE,
            set_temperature_scale,
            schema=TEMPERATURE_SCALE_SCHEMA,
        )


    async_add_entities(all_thermostats, True)


class NestThermostat(ClimateEntity, NestDevice):
    """Representation of a Nest thermostat."""

    def __init__(self, structure, device, temp_unit):
        """Initialize the thermostat."""
        super().__init__(structure, device)
        self.unit = temp_unit

        self._fan_modes = [FAN_ON, FAN_AUTO]

        # Set the default supported features
        self._support_flags = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

        # Not all nest devices support cooling and heating remove unused
        self._operation_list = []

        if self.device.can_heat and self.device.can_cool:
            self._operation_list.append(HVAC_MODE_AUTO)
            self._support_flags = self._support_flags | SUPPORT_TARGET_TEMPERATURE_RANGE

        # Add supported nest thermostat features
        if self.device.can_heat:
            self._operation_list.append(HVAC_MODE_HEAT)

        if self.device.can_cool:
            self._operation_list.append(HVAC_MODE_COOL)

        self._operation_list.append(HVAC_MODE_OFF)

        # feature of device
        self._has_fan = self.device.has_fan
        if self._has_fan:
            self._support_flags = self._support_flags | SUPPORT_FAN_MODE

        self._unique_id = self.device.device_id

        # data attributes
        self._away = None
        self._location = None
        self._name = None
        self._current_humidity = None
        self._target_temperature = None
        self._current_temperature = None
        self._temperature_scale = None
        self._mode = None
        self._action = None
        self._fan = None
        self._eco_temperature = None
        self._is_locked = None
        self._locked_temperature = None
        self._min_temperature = None
        self._max_temperature = None
        self._temperature_unit = None
        self._structure_name = None

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._temperature_unit

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        if self._mode == NEST_MODE_ECO:
            if self.device.previous_mode in MODE_NEST_TO_HASS:
                return MODE_NEST_TO_HASS[self.device.previous_mode]

            # previous_mode not supported so return the first compatible mode
            return self._operation_list[0]

        return MODE_NEST_TO_HASS[self._mode]

    @property
    def hvac_action(self):
        """Return the current hvac action."""
        return ACTION_NEST_TO_HASS[self._action]

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if self._mode not in (NEST_MODE_HEAT_COOL, NEST_MODE_ECO):
            return self._target_temperature
        return None

    @property
    def target_temperature_low(self):
        """Return the lower bound temperature we try to reach."""
        if self._mode == NEST_MODE_ECO:
            return self._eco_temperature[0]
        if self._mode == NEST_MODE_HEAT_COOL:
            return self._target_temperature[0]
        return None

    @property
    def target_temperature_high(self):
        """Return the upper bound temperature we try to reach."""
        if self._mode == NEST_MODE_ECO:
            return self._eco_temperature[1]
        if self._mode == NEST_MODE_HEAT_COOL:
            return self._target_temperature[1]
        return None

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temp = None
        target_temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        target_temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if self._mode == NEST_MODE_HEAT_COOL:
            if target_temp_low is not None and target_temp_high is not None:
                temp = (target_temp_low, target_temp_high)
                _LOGGER.debug(f"Nest set_temperature-output-value={temp}")
        else:
            temp = kwargs.get(ATTR_TEMPERATURE)
            _LOGGER.debug(f"Nest set_temperature-output-value={temp}")
        try:
            if temp is not None:
                self.device.target = temp
        except APIError as api_error:
            _LOGGER.error(f"An error occurred while setting temperature: {api_error}")
            # restore target temperature
            self.schedule_update_ha_state(True)

    def set_eco_mode(self, eco_mode):
        """Set Eco mode."""
        self.device.mode = NEST_MODE_ECO if eco_mode else self.device.previous_mode

    def set_fan_timer(self, duration):
        """Set fan timer."""
        if self._has_fan:
            self.device.fan_timer = duration

    def set_temperature_scale(self, temperature_scale):
        """Set unit of measurement."""
        self.device.temperature_scale = temperature_scale

    def set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        self.device.mode = MODE_HASS_TO_NEST[hvac_mode]

    @property
    def hvac_modes(self):
        """List of available operation modes."""
        return self._operation_list

    @property
    def preset_mode(self):
        """Return current preset mode."""
        if self._away and self._mode == NEST_MODE_ECO:
            return PRESET_AWAY_AND_ECO

        if self._away:
            return PRESET_AWAY

        if self._mode == NEST_MODE_ECO:
            return PRESET_ECO

        return PRESET_NONE

    @property
    def preset_modes(self):
        """Return preset modes."""
        return PRESET_MODES

    def set_preset_mode(self, preset_mode):
        """Set preset mode."""
        if preset_mode == self.preset_mode:
            return

        need_away = preset_mode in (PRESET_AWAY, PRESET_AWAY_AND_ECO)
        need_eco = preset_mode in (PRESET_ECO, PRESET_AWAY_AND_ECO)
        is_away = self._away
        is_eco = self._mode == NEST_MODE_ECO

        if is_away != need_away:
            self.structure.away = need_away

        if is_eco != need_eco:
            self.set_eco_mode(need_eco)

    @property
    def fan_mode(self):
        """Return whether the fan is on."""
        if self._has_fan:
            # Return whether the fan is on
            return FAN_ON if self._fan else FAN_AUTO
        # No Fan available so disable slider
        return None

    @property
    def fan_modes(self):
        """List of available fan modes."""
        if self._has_fan:
            return self._fan_modes
        return None

    def set_fan_mode(self, fan_mode):
        """Turn fan on/off."""
        if self._has_fan:
            self.device.fan = fan_mode.lower()

    @property
    def min_temp(self):
        """Identify min_temp in Nest API or defaults if not available."""
        return self._min_temperature

    @property
    def max_temp(self):
        """Identify max_temp in Nest API or defaults if not available."""
        return self._max_temperature

    def update(self):
        """Cache value from Python-nest."""
        self._location = self.device.where
        self._name = self.device.name_long
        self._current_humidity = self.device.humidity
        self._current_temperature = self.device.temperature
        self._mode = self.device.mode
        self._action = self.device.hvac_state
        self._target_temperature = self.device.target
        self._fan = self.device.fan
        self._away = self.structure.away == STATE_AWAY
        self._eco_temperature = self.device.eco_temperature
        self._locked_temperature = self.device.locked_temperature
        self._min_temperature = self.device.min_temperature
        self._max_temperature = self.device.max_temperature
        self._is_locked = self.device.is_locked
        self._temperature_scale = self.device.temperature_scale
        self._temperature_unit = TEMP_UNIT_MAP[self.device.temperature_scale]
        self._structure_name = self.structure.name

    @property
    def state_attributes(self):
        attrs = {**super().state_attributes, **super().device_state_attributes}

        if self._structure_name is not None:
            attrs[ATTR_STRUCTURE] = self._structure_name

        if self._temperature_scale is not None:
            attrs[ATTR_TEMPERATURE_SCALE] = self._temperature_scale

        if self._current_humidity is not None and not self._support_flags & SUPPORT_TARGET_HUMIDITY:
            attrs[ATTR_CURRENT_HUMIDITY] = self._current_humidity

        return attrs

class NestThermostatHumidistat(NestThermostat):
    """Representation of a Nest thermostat."""

    def __init__(self, structure, device, temp_unit, client, coordinator, id):
        """Initialize the thermostat."""
        super().__init__(structure, device, temp_unit)
        self.client = client
        self.coordinator = coordinator
        self.id = id

        self._support_flags = self._support_flags | SUPPORT_TARGET_HUMIDITY

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

#    @callback
#    def _async_consume_update(self):
#        self.update()
#        await self.hass.async_add_executor_job(self.update)

#        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
#            self.coordinator.async_add_listener(self._async_consume_update)
        )

    async def async_update(self):
        """Update the entity.

        Only used by the generic entity update service.
        """

        # Ignore manual update requests if the entity is disabled
        if not self.enabled:
            return

        await self.hass.async_add_executor_job(self.update)
        await self.coordinator.async_request_refresh()

    @property
    def min_humidity(self):
        """Return the min target humidity."""
        return NEST_HUMIDITY_MIN

    @property
    def max_humidity(self):
        """Return the max target humidity."""
        return NEST_HUMIDITY_MAX

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._current_humidity

    @property
    def target_humidity(self):
        """Return the target humidity."""
        return self._target_humidity

    def set_humidity(self, humidity):
        """Set new target humidity."""
        humidity = int(round(float(humidity) / NEST_HUMIDITY_STEP) * NEST_HUMIDITY_STEP)
        if humidity < NEST_HUMIDITY_MIN:
            humidity = NEST_HUMIDITY_MIN
        if humidity > NEST_HUMIDITY_MAX:
            humidity = NEST_HUMIDITY_MAX
        self.client.thermostat_set_target_humidity(self.id, humidity)

    @property
    def _target_humidity(self):
        """Return the minimum humidity."""
        return self.coordinator.data[self.id].get("target_humidity")

    @property
    def _thermostat_temperature(self):
        """Return the minimum humidity."""
        return self.coordinator.data[self.id].get("backplate_temperature")

    @property
    def state_attributes(self):
        attrs = super().state_attributes
        if self._thermostat_temperature is not None:
            attrs[ATTR_THERMOSTAT_TEMPERATURE] = self._thermostat_temperature
        return attrs

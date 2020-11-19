"""Custom Component"""

"""Class to hold all custom accessories."""
import logging

from pyhap.const import CATEGORY_THERMOSTAT

from custom_components.nest.const import (
    ATTR_ECO_MODE,
    ATTR_TEMPERATURE_SCALE,
    ATTR_THERMOSTAT_TEMPERATURE,
    DOMAIN as NEST_DOMAIN,
    NEST_HUMIDITY_MAX,
    NEST_HUMIDITY_MIN,
    NEST_HUMIDITY_STEP,
    PRESET_AWAY_AND_ECO,
    SERVICE_SET_ECO_MODE,
    SERVICE_SET_TEMPERATURE_SCALE,
    STATE_AUTO,
    TEMP_SCALE_C,
    TEMP_SCALE_F,
)
from homeassistant.components.climate.const import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_ECO,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    SUPPORT_TARGET_HUMIDITY,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import callback

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_COOLING_THRESHOLD_TEMPERATURE,
    CHAR_CURRENT_HEATING_COOLING,
    CHAR_CURRENT_HUMIDITY,
    CHAR_CURRENT_TEMPERATURE,
    CHAR_HEATING_THRESHOLD_TEMPERATURE,
    CHAR_NAME,
    CHAR_ON,
    CHAR_TARGET_HEATING_COOLING,
    CHAR_TARGET_HUMIDITY,
    CHAR_TARGET_TEMPERATURE,
    CHAR_TEMP_DISPLAY_UNITS,
    CONF_SERVICE_NAME_PREFIX,
    PROP_CELSIUS,
    PROP_MAX_VALUE,
    PROP_MIN_STEP,
    PROP_MIN_VALUE,
    SERV_FAN,
    SERV_SWITCH,
    SERV_TEMPERATURE_SENSOR,
    SERV_THERMOSTAT,
)
from .util import (
    convert_to_float,
    temperature_to_homekit,
    temperature_to_states,
)

_LOGGER = logging.getLogger(__name__)

HK_MIN_TEMP = 10
HK_MAX_TEMP = 38

DISPLAY_UNIT_TO_HK = {
    TEMP_SCALE_C: 0,
    TEMP_SCALE_F: 1,
}

DISPLAY_UNIT_TO_HASS = {c: s for s, c in DISPLAY_UNIT_TO_HK.items()}

CURRENT_STATE_TO_HK = {
    CURRENT_HVAC_IDLE: 0,
    CURRENT_HVAC_HEAT: 1,
    CURRENT_HVAC_COOL: 2,
}

TARGET_STATE_TO_HK = {
    HVAC_MODE_OFF: 0,
    HVAC_MODE_HEAT: 1,
    HVAC_MODE_COOL: 2,
    HVAC_MODE_AUTO: 3,
}

TARGET_STATE_TO_HASS = {c: s for s, c in TARGET_STATE_TO_HK.items()}


@TYPES.register("NestThermostat")
class NestThermostat(HomeAccessory):
    """Generate a NestThermostat accessory."""

    def __init__(self, *args):
        """Initialize a NestThermostat accessory object."""
        super().__init__(*args, category=CATEGORY_THERMOSTAT)
        state = self.hass.states.get(self.entity_id)
        prefix = self.config.get(CONF_SERVICE_NAME_PREFIX, self.display_name)

        self._features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        self._unit = self.hass.config.units.temperature_unit
        self._min_temp, self._max_temp = self._get_temperature_range()

        thermostat_chars = [
            CHAR_NAME,
            CHAR_CURRENT_HEATING_COOLING,
            CHAR_TARGET_HEATING_COOLING,
            CHAR_CURRENT_TEMPERATURE,
            CHAR_TARGET_TEMPERATURE,
            CHAR_TEMP_DISPLAY_UNITS,
            CHAR_CURRENT_HUMIDITY,
            CHAR_COOLING_THRESHOLD_TEMPERATURE,
            CHAR_HEATING_THRESHOLD_TEMPERATURE,
        ]
        if self._features & SUPPORT_TARGET_HUMIDITY:
            thermostat_chars.append(CHAR_TARGET_HUMIDITY)

        serv_thermostat = self.add_preload_service(SERV_THERMOSTAT, thermostat_chars)
        serv_thermostat.configure_char(CHAR_NAME, value=f"{prefix} Thermostat")

        self.char_thermostat_current_state = serv_thermostat.configure_char(
            CHAR_CURRENT_HEATING_COOLING,
            value=0,
        )
        self.char_thermostat_target_state = serv_thermostat.configure_char(
            CHAR_TARGET_HEATING_COOLING,
            value=0,
        )
        self.char_thermostat_current_temperature = serv_thermostat.configure_char(
            CHAR_CURRENT_TEMPERATURE,
            value=21.0,
        )
        self.char_thermostat_target_temperature = serv_thermostat.configure_char(
            CHAR_TARGET_TEMPERATURE,
            value=21.0,
            properties={
                PROP_MIN_VALUE: max(self._min_temp, HK_MIN_TEMP),
                PROP_MAX_VALUE: min(self._max_temp, HK_MAX_TEMP),
#                PROP_MIN_STEP: 0.5,
            },
        )
        self.char_thermostat_display_units = serv_thermostat.configure_char(
            CHAR_TEMP_DISPLAY_UNITS,
            value=0,
        )
        self.char_thermostat_current_humidity = serv_thermostat.configure_char(
            CHAR_CURRENT_HUMIDITY,
            value=0,
        )
        self.char_thermostat_cooling_threshold = serv_thermostat.configure_char(
            CHAR_COOLING_THRESHOLD_TEMPERATURE,
            value=23.0,
            properties={
                PROP_MIN_VALUE: max(self._min_temp, HK_MIN_TEMP),
                PROP_MAX_VALUE: min(self._max_temp, HK_MAX_TEMP),
#                PROP_MIN_STEP: 0.5,
            },
        )
        self.char_thermostat_heating_threshold = serv_thermostat.configure_char(
            CHAR_HEATING_THRESHOLD_TEMPERATURE,
            value=19.0,
            properties={
                PROP_MIN_VALUE: max(self._min_temp, HK_MIN_TEMP),
                PROP_MAX_VALUE: min(self._max_temp, HK_MAX_TEMP),
#                PROP_MIN_STEP: 0.5,
            },
        )

        if CHAR_TARGET_HUMIDITY in thermostat_chars:
            self.char_thermostat_target_humidity = serv_thermostat.configure_char(
                CHAR_TARGET_HUMIDITY,
                value=35,
                # We do not set a max humidity because
                # homekit currently has a bug that will show the lower bound
                # shifted upwards.  For example if you have a max humidity
                # of 80% homekit will give you the options 20%-100% instead
                # of 0-80%
                properties={
#                    PROP_MIN_VALUE: NEST_HUMIDITY_MIN,
#                    PROP_MAX_VALUE: NEST_HUMIDITY_MAX,
                    PROP_MIN_STEP: NEST_HUMIDITY_STEP,
                },
            )

        # Add temperature sensor service for temperature at thermostat
        if ATTR_THERMOSTAT_TEMPERATURE in state.attributes:
            serv_temperature = self.add_preload_service(SERV_TEMPERATURE_SENSOR, [CHAR_NAME, CHAR_CURRENT_TEMPERATURE])
            serv_temperature.configure_char(CHAR_NAME, value=f"{prefix} Temperature")

            self.char_sensor_temperature = serv_temperature.configure_char(
                CHAR_CURRENT_TEMPERATURE,
                value=0,
                properties=PROP_CELSIUS,
            )

        # Add switch service for Eco mode
        serv_eco_mode = self.add_preload_service(SERV_SWITCH, [CHAR_NAME, CHAR_ON])
        serv_eco_mode.configure_char(CHAR_NAME, value=f"{prefix} Thermostat Eco Mode")

        self.char_eco_mode_on = serv_eco_mode.configure_char(
            CHAR_ON,
            value=False,
            setter_callback=self._set_eco_mode,
        )

        # Add switch service for manual fan control
        serv_fan_mode = self.add_preload_service(SERV_FAN, [CHAR_NAME, CHAR_ON])
        serv_fan_mode.configure_char(CHAR_NAME, value=f"{prefix} Thermostat Fan")

        self.char_fan_mode_on = serv_fan_mode.configure_char(
            CHAR_ON,
            value=False,
            setter_callback=self._set_fan_mode,
        )

        self.async_update_state(state)

        serv_thermostat.setter_callback = self._set_thermostat_chars

    def _get_preset_mode(self, state):
        return state.attributes.get(ATTR_PRESET_MODE)

    def _get_target_heating_cooling_state(self, new_state):
        hk_target_state = 0
        hvac_mode = new_state.state
        attrs = new_state.attributes
        preset_mode = self._get_preset_mode(new_state)
        if preset_mode in (PRESET_ECO, PRESET_AWAY_AND_ECO):
            hvac_mode = HVAC_MODE_AUTO
        if hvac_mode in TARGET_STATE_TO_HK:
            hk_target_state = TARGET_STATE_TO_HK[hvac_mode]
        else:
            hk_target_state = TARGET_STATE_TO_HK[HVAC_MODE_OFF]
        return hk_target_state

    def _get_temperature_range(self):
        """Return min and max temperature range."""
        min_temp = self.hass.states.get(self.entity_id).attributes.get(ATTR_MIN_TEMP)
        min_temp = self._temperature_to_homekit(min_temp) if min_temp else DEFAULT_MIN_TEMP
        min_temp = round(min_temp * 2) / 2

        max_temp = self.hass.states.get(self.entity_id).attributes.get(ATTR_MAX_TEMP)
        max_temp = self._temperature_to_homekit(max_temp) if max_temp else DEFAULT_MAX_TEMP
        max_temp = round(max_temp * 2) / 2

        return min_temp, max_temp

    def _temperature_to_homekit(self, temp):
        return temperature_to_homekit(temp, self._unit)

    def _temperature_to_states(self, temp):
        return temperature_to_states(temp, self._unit)

    def _set_thermostat_chars(self, char_values):
        _LOGGER.debug("Thermostat _set_chars: %s", char_values)
        domain = DOMAIN
        service = None
        params = {}
        events = []

        state = self.hass.states.get(self.entity_id)

        if CHAR_TARGET_HEATING_COOLING in char_values:
            # Homekit will reset the mode when VIEWING the temp
            # Ignore it if its the same mode
            hk_target_state = self._get_target_heating_cooling_state(state)
            if char_values[CHAR_TARGET_HEATING_COOLING] != hk_target_state:
                service = SERVICE_SET_HVAC_MODE
                params[ATTR_HVAC_MODE] = TARGET_STATE_TO_HASS[char_values[CHAR_TARGET_HEATING_COOLING]]
                events.append(
                    f"{CHAR_TARGET_HEATING_COOLING} to {char_values[CHAR_TARGET_HEATING_COOLING]}"
                )

        if CHAR_TARGET_TEMPERATURE in char_values:
            preset_mode = self._get_preset_mode(state)
            if preset_mode in [PRESET_ECO, PRESET_AWAY_AND_ECO]:
                pass
            else:
                service = SERVICE_SET_TEMPERATURE
                params[ATTR_TEMPERATURE] = self._temperature_to_states(char_values[CHAR_TARGET_TEMPERATURE])
                events.append(
                    f"{CHAR_TARGET_TEMPERATURE} to {char_values[CHAR_TARGET_TEMPERATURE]}°C"
                )

        if CHAR_TEMP_DISPLAY_UNITS in char_values:
            if char_values[CHAR_TEMP_DISPLAY_UNITS] in DISPLAY_UNIT_TO_HASS:
                temperature_scale = DISPLAY_UNIT_TO_HASS[char_values[CHAR_TEMP_DISPLAY_UNITS]]
                domain = NEST_DOMAIN
                service = SERVICE_SET_TEMPERATURE_SCALE
                params[ATTR_TEMPERATURE_SCALE] = temperature_scale
                events.append(
                    f"{CHAR_TEMP_DISPLAY_UNITS} to {char_values[CHAR_TEMP_DISPLAY_UNITS]}"
                )

        if CHAR_COOLING_THRESHOLD_TEMPERATURE in char_values or CHAR_HEATING_THRESHOLD_TEMPERATURE in char_values:
            preset_mode = self._get_preset_mode(state)
            if preset_mode in [PRESET_ECO, PRESET_AWAY_AND_ECO]:
                cooling_threshold = state.attributes.get(ATTR_TARGET_TEMP_HIGH)
                if isinstance(cooling_threshold, (int, float)):
                    hk_cooling_threshold = self._temperature_to_homekit(cooling_threshold)
                    self.char_thermostat_cooling_threshold.set_value(hk_cooling_threshold)
                heating_threshold = state.attributes.get(ATTR_TARGET_TEMP_LOW)
                if isinstance(heating_threshold, (int, float)):
                    hk_heating_threshold = self._temperature_to_homekit(heating_threshold)
                    self.char_thermostat_heating_threshold.set_value(hk_heating_threshold)
                pass
            else:
                service = SERVICE_SET_TEMPERATURE
                high = self.char_thermostat_cooling_threshold.value
                low = self.char_thermostat_heating_threshold.value
                if CHAR_COOLING_THRESHOLD_TEMPERATURE in char_values:
                    events.append(
                        f"{CHAR_COOLING_THRESHOLD_TEMPERATURE} to {char_values[CHAR_COOLING_THRESHOLD_TEMPERATURE]}°C"
                    )
                    high = char_values[CHAR_COOLING_THRESHOLD_TEMPERATURE]
                if CHAR_HEATING_THRESHOLD_TEMPERATURE in char_values:
                    events.append(
                        f"{CHAR_HEATING_THRESHOLD_TEMPERATURE} to {char_values[CHAR_HEATING_THRESHOLD_TEMPERATURE]}°C"
                    )
                    low = char_values[CHAR_HEATING_THRESHOLD_TEMPERATURE]
                params[ATTR_TARGET_TEMP_HIGH] = self._temperature_to_states(min(high, self._max_temp))
                params[ATTR_TARGET_TEMP_LOW] = self._temperature_to_states(max(low, self._min_temp))

        if CHAR_TARGET_HUMIDITY in char_values:
            if char_values[CHAR_TARGET_HUMIDITY] > NEST_HUMIDITY_MAX:
                char_values[CHAR_TARGET_HUMIDITY] = NEST_HUMIDITY_MAX
                self.char_thermostat_target_humidity.set_value(char_values[CHAR_TARGET_HUMIDITY])
            if char_values[CHAR_TARGET_HUMIDITY] < NEST_HUMIDITY_MIN:
                char_values[CHAR_TARGET_HUMIDITY] = NEST_HUMIDITY_MIN
                self.char_thermostat_target_humidity.set_value(char_values[CHAR_TARGET_HUMIDITY])
            service = SERVICE_SET_HUMIDITY
            params[ATTR_HUMIDITY] = char_values[CHAR_TARGET_HUMIDITY]
            events.append(
                f"{CHAR_TARGET_HUMIDITY} to {char_values[CHAR_TARGET_HUMIDITY]}"
            )

        if service:
            params[ATTR_ENTITY_ID] = self.entity_id
            self.call_service(domain, service, params, ", ".join(events))

    def _set_eco_mode(self, value):
        """Move switch state to value if call came from HomeKit."""
        _LOGGER.debug("%s: Set Eco mode state to %s", self.entity_id, value)
        params = {
            ATTR_ENTITY_ID: self.entity_id,
            ATTR_ECO_MODE: value,
        }
        service = SERVICE_SET_ECO_MODE
        event = f"Eco mode: {CHAR_ON} to {value}"
        self.call_service(NEST_DOMAIN, service, params, event)

    def _set_fan_mode(self, value):
        """Move switch state to value if call came from HomeKit."""
        state = self.hass.states.get(self.entity_id)
        hvac_action = state.attributes.get(ATTR_HVAC_ACTION)
        hvac_mode = state.state
        if hvac_action in [CURRENT_HVAC_HEAT, CURRENT_HVAC_COOL] or hvac_mode == HVAC_MODE_OFF:
            fan = state.attributes.get(ATTR_FAN_MODE) == STATE_ON and hvac_action == CURRENT_HVAC_IDLE
            self.char_fan_mode_on.set_value(fan)
            pass
        else:
            _LOGGER.debug("%s: Set fan mode state to %s", self.entity_id, value)
            fan_mode = STATE_ON if value else STATE_OFF
            params = {
                ATTR_ENTITY_ID: self.entity_id,
                ATTR_FAN_MODE: fan_mode,
            }
            service = SERVICE_SET_FAN_MODE
            event = f"Fan mode: {CHAR_ON} to {fan_mode}"
            self.call_service(DOMAIN, service, params, event)

    @callback
    def async_update_state(self, new_state):
        attrs = new_state.attributes

        # Update current heating cooling state
        hvac_action = attrs.get(ATTR_HVAC_ACTION)
        if hvac_action in CURRENT_STATE_TO_HK:
            hk_current_state = CURRENT_STATE_TO_HK[hvac_action]
            if self.char_thermostat_current_state.value != hk_current_state:
                self.char_thermostat_current_state.set_value(hk_current_state)

        # Update target heating cooling state
        hk_target_state = self._get_target_heating_cooling_state(new_state)
        if self.char_thermostat_target_state.value != hk_target_state:
            self.char_thermostat_target_state.set_value(hk_target_state)

        # Update current temperature
        current_temperature = attrs.get(ATTR_CURRENT_TEMPERATURE)
        if isinstance(current_temperature, (int, float)):
            hk_current_temperature = self._temperature_to_homekit(current_temperature)
            if self.char_thermostat_current_temperature.value != hk_current_temperature:
                self.char_thermostat_current_temperature.set_value(hk_current_temperature)

        # Update target temperature
        target_temperature = attrs.get(ATTR_TEMPERATURE)
        if isinstance(target_temperature, (int, float)):
            hk_target_temperature = self._temperature_to_homekit(target_temperature)
            if self.char_thermostat_target_temperature.value != hk_target_temperature:
                self.char_thermostat_target_temperature.set_value(hk_target_temperature)

        # Update display units
        temperature_scale = attrs.get(ATTR_TEMPERATURE_SCALE)
        if temperature_scale in DISPLAY_UNIT_TO_HK:
            hk_display_units = DISPLAY_UNIT_TO_HK[temperature_scale]
            if self.char_thermostat_display_units.value != hk_display_units:
                self.char_thermostat_display_units.set_value(hk_display_units)

        # Update current humidity
        current_humidity = convert_to_float(attrs.get(ATTR_CURRENT_HUMIDITY))
        if isinstance(current_humidity, (int, float)):
            hk_current_humidity = convert_to_float(current_humidity)
            if self.char_thermostat_current_humidity.value != hk_current_humidity:
                self.char_thermostat_current_humidity.set_value(hk_current_humidity)

        # Update cooling threshold temperature
        cooling_threshold = attrs.get(ATTR_TARGET_TEMP_HIGH)
        if isinstance(cooling_threshold, (int, float)):
            hk_cooling_threshold = self._temperature_to_homekit(cooling_threshold)
            if self.char_thermostat_cooling_threshold.value != hk_cooling_threshold:
                self.char_thermostat_cooling_threshold.set_value(hk_cooling_threshold)

        # Update heating threshold temperature
        heating_threshold = attrs.get(ATTR_TARGET_TEMP_LOW)
        if isinstance(heating_threshold, (int, float)):
            hk_heating_threshold = self._temperature_to_homekit(heating_threshold)
            if self.char_thermostat_heating_threshold.value != hk_heating_threshold:
                self.char_thermostat_heating_threshold.set_value(hk_heating_threshold)

        # Update target humidity if supported
        if self._features & SUPPORT_TARGET_HUMIDITY:
            target_humidity = convert_to_float(attrs.get(ATTR_HUMIDITY))
            if isinstance(target_humidity, (int, float)):
                hk_target_humidity = convert_to_float(target_humidity)
                if self.char_thermostat_target_humidity.value != hk_target_humidity:
                    self.char_thermostat_target_humidity.set_value(hk_target_humidity)

        # Update temperature sensor
        if ATTR_THERMOSTAT_TEMPERATURE in attrs:
            temperature = convert_to_float(attrs.get(ATTR_THERMOSTAT_TEMPERATURE))
            if isinstance(temperature, (int, float)):
                if self.char_sensor_temperature.value != temperature:
                    self.char_sensor_temperature.set_value(temperature)

        # Update Eco mode state
        eco_mode = self._get_preset_mode(new_state) in [PRESET_ECO, PRESET_AWAY_AND_ECO]
        if self.char_eco_mode_on.value != eco_mode:
            self.char_eco_mode_on.set_value(eco_mode)

        # Update fan state
        fan_mode = attrs.get(ATTR_FAN_MODE) == STATE_ON and hvac_action == CURRENT_HVAC_IDLE
        if self.char_fan_mode_on.value != fan_mode:
            self.char_fan_mode_on.set_value(fan_mode)

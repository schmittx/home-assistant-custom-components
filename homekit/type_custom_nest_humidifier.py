"""Custom Component"""

"""Class to hold all custom accessories."""
import logging

from pyhap.const import CATEGORY_HUMIDIFIER

from custom_components.nest.const import (
    ATTR_HUMIDIFIER_ACTION,
    NEST_HUMIDITY_MAX,
    NEST_HUMIDITY_MIN,
    NEST_HUMIDITY_STEP,
    STATE_HUMIDIFYING,
)
from homeassistant.components.climate.const import ATTR_CURRENT_HUMIDITY
from homeassistant.components.humidifier.const import (
    ATTR_HUMIDITY,
    DOMAIN,
    SERVICE_SET_HUMIDITY,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import callback

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_ACTIVE,
    CHAR_CURRENT_HUMIDIFIER_DEHUMIDIFIER,
    CHAR_CURRENT_HUMIDITY,
    CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY,
    CHAR_NAME,
    CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER,
    CONF_SERVICE_NAME_PREFIX,
    PROP_MAX_VALUE,
    PROP_MIN_STEP,
    PROP_MIN_VALUE,
    SERV_HUMIDIFIER_DEHUMIDIFIER,
)
from .util import convert_to_float

_LOGGER = logging.getLogger(__name__)


@TYPES.register("NestHumidifier")
class NestHumidifier(HomeAccessory):
    """Generate a NestHumidifier accessory."""

    def __init__(self, *args):
        """Initialize a NestHumidifier accessory object."""
        super().__init__(*args, category=CATEGORY_HUMIDIFIER)
        state = self.hass.states.get(self.entity_id)
        prefix = self.config.get(CONF_SERVICE_NAME_PREFIX, self.display_name)

        humidifier_chars = [
            CHAR_NAME,
            CHAR_CURRENT_HUMIDITY,
            CHAR_CURRENT_HUMIDIFIER_DEHUMIDIFIER,
            CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER,
            CHAR_ACTIVE,
            CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY,
        ]
        serv_humidifier = self.add_preload_service(SERV_HUMIDIFIER_DEHUMIDIFIER, humidifier_chars)
        serv_humidifier.configure_char(CHAR_NAME, value=f"{prefix} Humidifier")

        self.char_current_humidity = serv_humidifier.configure_char(
            CHAR_CURRENT_HUMIDITY,
            value=0,
        )
        self.char_current_state = serv_humidifier.configure_char(
            CHAR_CURRENT_HUMIDIFIER_DEHUMIDIFIER,
            value=0,
        )
        self.char_target_state = serv_humidifier.configure_char(
            CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER,
            value=1,
            valid_values={
                "Humidifier": 1,
            },
        )
        self.char_active = serv_humidifier.configure_char(
            CHAR_ACTIVE,
            value=False,
        )
        self.char_target_humidity = serv_humidifier.configure_char(
            CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY,
            value=35,
            properties={
#                PROP_MIN_VALUE: NEST_HUMIDITY_MIN,
#                PROP_MAX_VALUE: NEST_HUMIDITY_MAX,
                PROP_MIN_STEP: NEST_HUMIDITY_STEP,
            },
        )

        self.async_update_state(state)

        serv_humidifier.setter_callback = self._set_humidifier_chars

    def _set_humidifier_chars(self, char_values):
        _LOGGER.debug("Humidifier _set_chars: %s", char_values)
        domain = DOMAIN
        service = None
        params = {}
        events = []

        state = self.hass.states.get(self.entity_id)

        if CHAR_ACTIVE in char_values:
            service = SERVICE_TURN_ON if bool(char_values[CHAR_ACTIVE]) else SERVICE_TURN_OFF
            events.append(
                f"{CHAR_ACTIVE} to {char_values[CHAR_ACTIVE]}"
            )

        if CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY in char_values:
            if char_values[CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY] > NEST_HUMIDITY_MAX:
                char_values[CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY] = NEST_HUMIDITY_MAX
                self.char_target_humidity.set_value(char_values[CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY])
            if char_values[CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY] < NEST_HUMIDITY_MIN:
                char_values[CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY] = NEST_HUMIDITY_MIN
                self.char_target_humidity.set_value(char_values[CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY])
            service = SERVICE_SET_HUMIDITY
            params[ATTR_HUMIDITY] = char_values[CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY]
            events.append(
                f"{CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY} to {char_values[CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY]}"
            )

        if service:
            params[ATTR_ENTITY_ID] = self.entity_id
            self.call_service(domain, service, params, ", ".join(events))

    @callback
    def async_update_state(self, new_state):
        attrs = new_state.attributes

        # Update current humidity
        current_humidity = convert_to_float(attrs.get(ATTR_CURRENT_HUMIDITY))
        if isinstance(current_humidity, (int, float)):
            hk_current_humidity = convert_to_float(current_humidity)
            if self.char_current_humidity.value != hk_current_humidity:
                self.char_current_humidity.set_value(hk_current_humidity)

        # Update target humidity
        target_humidity = convert_to_float(attrs.get(ATTR_HUMIDITY))
        if isinstance(target_humidity, (int, float)):
            hk_target_humidity = convert_to_float(target_humidity)
            if self.char_target_humidity.value != hk_target_humidity:
                self.char_target_humidity.set_value(hk_target_humidity)

        # Update humidifier
        active = new_state.state == STATE_ON
        if self.char_active.value != active:
            self.char_active.set_value(active)
        humidifier_action = attrs.get(ATTR_HUMIDIFIER_ACTION) == STATE_HUMIDIFYING
        if active:
            if humidifier_action:
                humidifier_current_state = 2
            else:
                humidifier_current_state = 1
        else:
            humidifier_current_state = 0
        if self.char_current_state.value != humidifier_current_state:
            self.char_current_state.set_value(humidifier_current_state)

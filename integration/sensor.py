"""Numeric integration of data coming from a source sensor over time."""
from decimal import Decimal, DecimalException
import logging

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import (
    ATTR_SOURCE_ID,
    CONF_METHOD,
    CONF_ROUND_DIGITS,
    CONF_SOURCE_SENSOR,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_UNIT_PREFIX,
    CONF_UNIT_TIME,
    ICON,
    METHOD_LEFT,
    METHOD_RIGHT,
    METHOD_TRAPEZOIDAL,
    PREFIX_NONE,
    UNIT_PREFIXES,
    UNIT_TIME,
)

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the integration sensor based on a config entry."""
    conf = entry.data
    options = entry.options
    sensor = IntegrationSensor(
        source_entity=conf[CONF_SOURCE_SENSOR],
        name=options.get(CONF_NAME, conf[CONF_NAME]),
        round_digits=options.get(CONF_ROUND_DIGITS, conf[CONF_ROUND_DIGITS]),
        unit_prefix=conf[CONF_UNIT_PREFIX],
        unit_time=conf[CONF_UNIT_TIME],
        unit_of_measurement=conf.get(CONF_UNIT_OF_MEASUREMENT),
        integration_method=options.get(CONF_METHOD, conf[CONF_METHOD]),
        unique_id=entry.entry_id,
    )

    async_add_entities([sensor])


class IntegrationSensor(RestoreEntity):
    """Representation of an integration sensor."""

    def __init__(
        self,
        source_entity,
        name,
        round_digits,
        unit_prefix,
        unit_time,
        unit_of_measurement,
        integration_method,
        unique_id=None,
    ):
        """Initialize the integration sensor."""
        self._sensor_source_id = source_entity
        self._round_digits = round_digits
        self._state = 0
        self._method = integration_method

        self._name = name

        if unit_of_measurement is None:
            self._unit_template = (
                f"{'' if unit_prefix is PREFIX_NONE else unit_prefix}{{}}{unit_time}"
            )
            # we postpone the definition of unit_of_measurement to later
            self._unit_of_measurement = None
        else:
            self._unit_of_measurement = unit_of_measurement

        self._unit_prefix = UNIT_PREFIXES[unit_prefix]
        self._unit_time = UNIT_TIME[unit_time]
        self._async_unsub_state_changed = None
        self._unique_id = unique_id

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            try:
                self._state = Decimal(state.state)
            except ValueError as err:
                _LOGGER.warning("Could not restore last state: %s", err)

        @callback
        def calc_integration(event):
            """Handle the sensor state changes."""
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
            if (
                old_state is None
                or old_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]
                or new_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]
            ):
                return

            if self._unit_of_measurement is None:
                unit = new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
                self._unit_of_measurement = self._unit_template.format(
                    "" if unit is None else unit
                )

            try:
                # integration as the Riemann integral of previous measures.
                area = 0
                elapsed_time = (
                    new_state.last_updated - old_state.last_updated
                ).total_seconds()

                if self._method == METHOD_TRAPEZOIDAL:
                    area = (
                        (Decimal(new_state.state) + Decimal(old_state.state))
                        * Decimal(elapsed_time)
                        / 2
                    )
                elif self._method == METHOD_LEFT:
                    area = Decimal(old_state.state) * Decimal(elapsed_time)
                elif self._method == METHOD_RIGHT:
                    area = Decimal(new_state.state) * Decimal(elapsed_time)

                integral = area / (self._unit_prefix * self._unit_time)
                assert isinstance(integral, Decimal)
            except ValueError as err:
                _LOGGER.warning("While calculating integration: %s", err)
            except DecimalException as err:
                _LOGGER.warning(
                    "Invalid state (%s > %s): %s", old_state.state, new_state.state, err
                )
            except AssertionError as err:
                _LOGGER.error("Could not calculate integral: %s", err)
            else:
                self._state += integral
                self.async_write_ha_state()

        self._async_unsub_state_changed = async_track_state_change_event(
            self.hass, [self._sensor_source_id], calc_integration
        )

    async def async_will_remove_from_hass(self) -> None:
        """Handle removal from Home Assistant."""
        await super().async_will_remove_from_hass()
        if self._async_unsub_state_changed is not None:
            self._async_unsub_state_changed()
            self._async_unsub_state_changed = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return round(self._state, self._round_digits)

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {ATTR_SOURCE_ID: self._sensor_source_id}

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

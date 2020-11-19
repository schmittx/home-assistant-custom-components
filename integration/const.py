"""Constants used by the integration component."""
from homeassistant.const import TIME_DAYS, TIME_HOURS, TIME_MINUTES, TIME_SECONDS

ATTR_SOURCE_ID = "source"

CONF_METHOD = "method"
CONF_ROUND_DIGITS = "round"
CONF_SOURCE_SENSOR = "source"
CONF_UNIT_OF_MEASUREMENT = "unit"
CONF_UNIT_PREFIX = "unit_prefix"
CONF_UNIT_TIME = "unit_time"

DOMAIN = "integration"

ICON = "mdi:chart-histogram"

METHOD_LEFT = "left"
METHOD_RIGHT = "right"
METHOD_TRAPEZOIDAL = "trapezoidal"

PREFIX_NONE = "none"
PREFIX_KILO = "k"
PREFIX_MEGA = "M"
PREFIX_GIGA = "G"
PREFIX_TERA = "T"

INTEGRATION_METHODS = [METHOD_LEFT, METHOD_RIGHT, METHOD_TRAPEZOIDAL]

UNIT_PREFIXES = {
    PREFIX_NONE: 1,
    PREFIX_KILO: 10 ** 3,
    PREFIX_MEGA: 10 ** 6,
    PREFIX_GIGA: 10 ** 9,
    PREFIX_TERA: 10 ** 12,
}

UNIT_TIME = {
    TIME_SECONDS: 1,
    TIME_MINUTES: 60,
    TIME_HOURS: 60 * 60,
    TIME_DAYS: 24 * 60 * 60,
}

UNDO_UPDATE_LISTENER = "undo_update_listener"

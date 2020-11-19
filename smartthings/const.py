"""Custom Component"""

"""Constants used by the SmartThings component and platforms."""
from datetime import timedelta
import re

DOMAIN = "smartthings"

APP_OAUTH_CLIENT_NAME = "Home Assistant"
APP_OAUTH_SCOPES = ["r:devices:*"]
APP_NAME_PREFIX = "homeassistant."

CONF_APP_ID = "app_id"
CONF_CLOUDHOOK_URL = "cloudhook_url"
CONF_INSTALLED_APP_ID = "installed_app_id"
CONF_INSTANCE_ID = "instance_id"
CONF_LOCATION_ID = "location_id"
CONF_REFRESH_TOKEN = "refresh_token"

DATA_MANAGER = "manager"
DATA_BROKERS = "brokers"
EVENT_BUTTON = "smartthings.button"

SIGNAL_SMARTTHINGS_BUTTON = "smartthings_button"
SIGNAL_SMARTTHINGS_UPDATE = "smartthings_update"
SIGNAL_SMARTAPP_PREFIX = "smartthings_smartap_"

SETTINGS_INSTANCE_ID = "hassInstanceId"

SUBSCRIPTION_WARNING_LIMIT = 40

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

# Ordered 'specific to least-specific platform' in order for capabilities
# to be drawn-down and represented by the most appropriate platform.
SUPPORTED_PLATFORMS = [
    "climate",
    "fan",
    "light",
    "lock",
    "cover",
    "switch",
    "binary_sensor",
    "sensor",
    "scene",
]

IGNORED_CAPABILITIES = [
    "execute",
    "healthCheck",
    "ocf",
]

TOKEN_REFRESH_INTERVAL = timedelta(days=14)

VAL_UID = "^(?:([0-9a-fA-F]{32})|([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}))$"
VAL_UID_MATCHER = re.compile(VAL_UID)

# Custom Component
ATTRIBUTION =  "Data provided by SmartThings"
MANUFACTURER = "manufacturer"
MODEL = "MODEL"
DEVICE_INFO_MAP = {
    "Leviton Switch": {
        MANUFACTURER: "Leviton", MODEL: "DZS15-1LZ",
    },
    "Leviton 15A Switch": {
        MANUFACTURER: "Leviton", MODEL: "DZS15-1LZ",
    },
    "Leviton 3-Speed Fan Controller": {
        MANUFACTURER: "Leviton", MODEL: "VRF01-1LZ",
    },
    "Leviton Magnetic Low Voltage Dimmer": {
        MANUFACTURER: "Leviton", MODEL: "DZMX1-1LZ",
    },
    "Leviton Universal Dimmer": {
        MANUFACTURER: "Leviton", MODEL: "DZMX1-1LZ",
    },
    "Leviton Outlet": {
        MANUFACTURER: "Leviton", MODEL: "DZR15-1LZ",
    },
    "Dome Leak Sensor": {
        MANUFACTURER: "Dome", MODEL: "DMWS1",
    },
    "SmartThings Motion Sensor": {
        MANUFACTURER: "SmartThings", MODEL: "GP-U999SJVLBAA",
    },
    "Smart Plug": {
        MANUFACTURER: "SmartThings", MODEL: "GP-WOU019BBAWU",
    },
    "Schlage Touchscreen Deadbolt Door Lock": {
        MANUFACTURER: "Schlage", MODEL: "BE469NX",
    },
}
# Custom Component

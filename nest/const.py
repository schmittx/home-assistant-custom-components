"""Custom Component"""

"""Constants used by the Nest component."""
ATTR_ACTIVITY_DETECTED = "activity_detected"
ATTR_AWAY_MODE = "away_mode"
ATTR_BATTERY_HEALTH = "battery_health"
ATTR_CO_STATUS = "co_status"
ATTR_COLOR_STATUS = "color_status"
ATTR_DOORBELL_TRIGGERED = "doorbell_triggered"
ATTR_DURATION = "duration"
ATTR_ECO_MODE = "eco_mode"
ATTR_ETA = "eta"
ATTR_ETA_WINDOW = "eta_window"
ATTR_HUMIDIFIER_ACTION = "humidifier_action"
ATTR_HVAC_STATE = "hvac_state"
ATTR_MOTION_DETECTED = "motion_detected"
ATTR_ONLINE = "online"
ATTR_PERSON_DETECTED = "person_detected"
ATTR_SMOKE_STATUS = "smoke_status"
ATTR_SOUND_DETECTED = "sound_detected"
ATTR_STREAMING = "streaming"
ATTR_STRUCTURE = "structure"
ATTR_TEMPERATURE_SCALE = "temperature_scale"
ATTR_THERMOSTAT_TEMPERATURE = "thermostat_temperature"
ATTR_TRIP_ID = "trip_id"

ATTRIBUTION = "Data provided by Nest"

CAMERA_OFF_IMAGE_PATH = "/config/custom_components/nest/"
CAMERA_OFF_IMAGE_4_3 = f"{CAMERA_OFF_IMAGE_PATH}camera_offline_4_3.jpg"
CAMERA_OFF_IMAGE_16_9 = f"{CAMERA_OFF_IMAGE_PATH}camera_offline_16_9.jpg"

CONF_CAMERA = "camera"
CONF_STREAM_SOURCE = "stream_source"
CONF_USER_ID = "user_id"
CONF_WEB_CLIENT = "web_client"

DATA_CLIENT = "client"
DATA_CONFIG = "config"
DATA_COORDINATOR = "coordinator"
DATA_NEST = "nest"

DOMAIN = "nest"

MANUFACTURER = "Nest"

MODEL_CAMERA = "Camera"
MODEL_PROTECT = "Protect"
MODEL_STRUCTURE = "Structure"
MODEL_TEMPERATURE_SENSOR = "Temperature Sensor"
MODEL_THERMOSTAT = "Thermostat"

NEST_CONFIG_FILE = "nest.conf"

NEST_HUMIDITY_MIN = 10
NEST_HUMIDITY_MAX = 60
NEST_HUMIDITY_STEP = 5

PRESET_AWAY_AND_ECO = "Away and Eco"

SERVICE_CANCEL_ETA = "cancel_eta"
SERVICE_SET_AWAY_MODE = "set_away_mode"
SERVICE_SET_ECO_MODE = "set_eco_mode"
SERVICE_SET_ETA = "set_eta"
SERVICE_SET_FAN_TIMER = "set_fan_timer"
SERVICE_SET_TEMPERATURE_SCALE = "set_temperature_scale"

SIGNAL_NEST_UPDATE = "nest_update"

STATE_AUTO = "auto"
STATE_AWAY = "away"
STATE_COOLING = "cooling"
STATE_EMERGENCY = "emergency"
STATE_GREEN = "green"
STATE_HEAT_COOL = "heat-cool"
STATE_HEATING = "heating"
STATE_HUMIDIFYING = "humidifying"
STATE_OK = "ok"
STATE_REPLACE = "replace"
STATE_WARNING = "warning"

TEMP_SCALE_C = "C"
TEMP_SCALE_F = "F"

TYPE_ALL = "all"
TYPE_CAMERA = "camera"
TYPE_DOORBELL = "doorbell"
TYPE_SMOKE_CO_ALARM = "smoke_co_alarm"
TYPE_STRUCTURE = "structure"
TYPE_TEMPERATURE_SENSOR = "temperature_sensor"
TYPE_THERMOSTAT = "thermostat"

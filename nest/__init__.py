"""Custom Component"""

"""Support for Nest devices."""
from datetime import datetime, timedelta
import async_timeout
import logging
import threading

from nest import Nest
from nest.nest import APIError, AuthorizationError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_FILENAME,
    CONF_STRUCTURE,
    CONF_URL,
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
    STATE_HOME,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from . import local_auth
from .client import NestWebClient, ClientError
from .const import (
    ATTR_AWAY_MODE,
    ATTR_ETA,
    ATTR_ETA_WINDOW,
    ATTR_STRUCTURE,
    ATTR_TRIP_ID,
    ATTRIBUTION,
    CONF_CAMERA,
    CONF_STREAM_SOURCE,
    CONF_USER_ID,
    CONF_WEB_CLIENT,
    DATA_CLIENT,
    DATA_CONFIG,
    DATA_COORDINATOR,
    DATA_NEST,
    DOMAIN,
    MANUFACTURER,
    MODEL_CAMERA,
    MODEL_PROTECT,
    MODEL_STRUCTURE,
    MODEL_THERMOSTAT,
    NEST_CONFIG_FILE,
    SERVICE_CANCEL_ETA,
    SERVICE_SET_AWAY_MODE,
    SERVICE_SET_ETA,
    SIGNAL_NEST_UPDATE,
    STATE_AWAY,
)

_CONFIGURING = {}
_LOGGER = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = ["binary_sensor", "camera", "climate", "sensor", "switch"]

STREAM_SOURCE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CAMERA): cv.string,
        vol.Required(CONF_URL): cv.string,
    }
)

WEB_CLIENT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USER_ID): cv.string,
        vol.Required(CONF_ACCESS_TOKEN): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
                vol.Optional(CONF_STREAM_SOURCE, default=[]): vol.All(cv.ensure_list, [STREAM_SOURCE_SCHEMA]),
                vol.Optional(CONF_STRUCTURE, default=[]): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_WEB_CLIENT, default={}): WEB_CLIENT_SCHEMA,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SET_AWAY_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_AWAY_MODE): vol.In([STATE_AWAY, STATE_HOME]),
        vol.Optional(ATTR_STRUCTURE): vol.All(cv.ensure_list, [cv.string]),
    }
)

SET_ETA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ETA): cv.time_period,
        vol.Optional(ATTR_TRIP_ID): cv.string,
        vol.Optional(ATTR_ETA_WINDOW): cv.time_period,
        vol.Optional(ATTR_STRUCTURE): vol.All(cv.ensure_list, [cv.string]),
    }
)

CANCEL_ETA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TRIP_ID): cv.string,
        vol.Optional(ATTR_STRUCTURE): vol.All(cv.ensure_list, [cv.string]),
    }
)


def supported_device(client, device):
    if client is None:
        return False
    else:
        if hasattr(device, "name_long"):
            return bool(client.valid_device(device.name_long))
        else:
            return bool(client.valid_device(device.name))

def nest_update_event_broker(hass, nest):
    """
    Dispatch SIGNAL_NEST_UPDATE to devices when nest stream API received data.

    Runs in its own thread.
    """
    _LOGGER.debug("Listening for nest.update_event")

    while hass.is_running:
        nest.update_event.wait()

        if not hass.is_running:
            break

        nest.update_event.clear()
        _LOGGER.debug("Dispatching nest data update")
        dispatcher_send(hass, SIGNAL_NEST_UPDATE)

    _LOGGER.debug("Stop listening for nest.update_event")


async def async_setup(hass, config):
    """Set up Nest components."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    local_auth.initialize(hass, conf[CONF_CLIENT_ID], conf[CONF_CLIENT_SECRET])

    filename = config.get(CONF_FILENAME, NEST_CONFIG_FILE)
    access_token_cache_file = hass.config.path(filename)

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={"nest_conf_path": access_token_cache_file},
        )
    )

    # Store config to be used during entry setup
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DATA_CONFIG] = conf

    return True


async def async_setup_entry(hass, entry):
    """Set up Nest from a config entry."""
    nest = Nest(access_token=entry.data["tokens"]["access_token"])

    _LOGGER.debug("Proceeding with setup")
    conf = hass.data[DOMAIN].get(DATA_CONFIG, {})
    hass.data[DOMAIN][DATA_NEST] = NestBase(hass, conf, nest)
    if not await hass.async_add_job(hass.data[DOMAIN][DATA_NEST].initialize):
        return False

    if conf[CONF_WEB_CLIENT]:

#        user_id = conf[CONF_WEB_CLIENT][CONF_USER_ID]
#        access_token = conf[CONF_WEB_CLIENT][CONF_ACCESS_TOKEN]

#        client = NestWebClient(user_id, access_token)

        client = await hass.async_add_executor_job(
            NestWebClient,
            conf[CONF_WEB_CLIENT][CONF_USER_ID],
            conf[CONF_WEB_CLIENT][CONF_ACCESS_TOKEN],
        )

        if not client.valid_credentials:
            _LOGGER.error("Web client authentication failed")
            return False
        else:
            async def async_update_data():
                """Fetch data from API endpoint.

                This is the place to pre-process the data to lookup tables
                so entities can quickly look up their data.
                """
                try:
                    # Note: asyncio.TimeoutError and aiohttp.ClientError are already
                    # handled by the data update coordinator.
                    async with async_timeout.timeout(15):
                        return await hass.async_add_executor_job(client.get_update)
                except ClientError as err:
                    raise UpdateFailed(f"Error communicating with web client: {err}")

            coordinator = DataUpdateCoordinator(
                hass,
                _LOGGER,
                # Name of the data. For logging purposes.
                name=f"Nest Web Client ({conf[CONF_WEB_CLIENT][CONF_USER_ID]})",
                update_method=async_update_data,
                # Polling interval. Will only be polled if there are subscribers.
                update_interval=timedelta(seconds=30),
            )

            # Fetch initial data so we have data when entities subscribe
            await coordinator.async_refresh()


            _LOGGER.info("Web client authentication valid")
            hass.data[DOMAIN][DATA_CLIENT] = client
            hass.data[DOMAIN][DATA_COORDINATOR] = coordinator
            SUPPORTED_PLATFORMS.append("humidifier")

    for component in SUPPORTED_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    def validate_structures(target_structures):
        validated_structures = []
        for structure in nest.structures:
            if structure.name in target_structures:
                validated_structures.append(structure)
        return validated_structures

    def set_away_mode(service):
        """Set the away mode for a Nest structure."""
        target_structures = service.data.get(ATTR_STRUCTURE, hass.data[DOMAIN][DATA_NEST].local_structure)
        for structure in validate_structures(target_structures):
            _LOGGER.info(
                f"Setting away mode for: {structure.name} to: {service.data[ATTR_AWAY_MODE]}"
            )
            structure.away = service.data[ATTR_AWAY_MODE]

    def set_eta(service):
        """Set away mode to away and include ETA for a Nest structure."""
        target_structures = service.data.get(ATTR_STRUCTURE, hass.data[DOMAIN][DATA_NEST].local_structure)
        for structure in validate_structures(target_structures):
            if structure.thermostats:
                _LOGGER.info(
                    f"Setting away mode for: {structure.name} to: {STATE_AWAY}"
                )
                structure.away = STATE_AWAY

                now = datetime.utcnow()
                trip_id = service.data.get(
                    ATTR_TRIP_ID, f"trip_{int(now.timestamp())}"
                )
                eta_begin = now + service.data[ATTR_ETA]
                eta_window = service.data.get(ATTR_ETA_WINDOW, timedelta(minutes=1))
                eta_end = eta_begin + eta_window
                _LOGGER.info(
                    f"Setting ETA for trip: {trip_id}, ETA window starts at: {eta_begin} and ends at: {eta_end}"
                )
                structure.set_eta(trip_id, eta_begin, eta_end)
            else:
                _LOGGER.info(
                    f"No thermostats found in structure: {structure.name}, unable to set ETA"
                )

    def cancel_eta(service):
        """Cancel ETA for a Nest structure."""
        target_structures = service.data.get(ATTR_STRUCTURE, hass.data[DOMAIN][DATA_NEST].local_structure)
        for structure in validate_structures(target_structures):
            if structure.thermostats:
                trip_id = service.data[ATTR_TRIP_ID]
                _LOGGER.info(f"Cancelling ETA for trip: {trip_id}")
                structure.cancel_eta(trip_id)
            else:
                _LOGGER.info(
                    f"No thermostats found in structure: {structure.name}, unable to cancel ETA"
                )

    hass.services.async_register(
        DOMAIN, SERVICE_SET_AWAY_MODE, set_away_mode, schema=SET_AWAY_MODE_SCHEMA
    )

    hass.services.async_register(
        DOMAIN, SERVICE_SET_ETA, set_eta, schema=SET_ETA_SCHEMA
    )

    hass.services.async_register(
        DOMAIN, SERVICE_CANCEL_ETA, cancel_eta, schema=CANCEL_ETA_SCHEMA
    )

    @callback
    def start_up(event):
        """Start Nest update event listener."""
        threading.Thread(
            name="Nest update listener",
            target=nest_update_event_broker,
            args=(hass, nest),
        ).start()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_up)

    @callback
    def shut_down(event):
        """Stop Nest update event listener."""
        nest.update_event.set()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, shut_down)

    _LOGGER.debug("async_setup_nest is done")

    return True


class NestBase:
    """Structure Nest functions for hass."""

    def __init__(self, hass, conf, nest):
        """Init Nest Devices."""
        self.hass = hass
        self.nest = nest
        self.local_structure = conf[CONF_STRUCTURE]

    def initialize(self):
        """Initialize Nest."""
        try:
            # Do not optimize next statement, it is here for initialize
            # persistence Nest API connection.
            structure_names = [s.name for s in self.nest.structures]
            if not self.local_structure:
                self.local_structure = structure_names

        except (AuthorizationError, APIError, OSError) as err:
            _LOGGER.error(f"Connection error while accessing Nest web service: {err}")
            return False
        return True

    def structures(self):
        """Generate a list of structures."""
        try:
            for structure in self.nest.structures:
                if structure.name not in self.local_structure:
                    _LOGGER.debug(
                        f"Ignoring structure {structure.name}, not in {self.local_structure}"
                    )
                    continue
                yield structure

        except (AuthorizationError, APIError, OSError) as err:
            _LOGGER.error(f"Connection error while accessing Nest web service: {err}")

    def thermostats(self):
        """Generate a list of thermostats."""
        return self._devices("thermostats")

    def smoke_co_alarms(self):
        """Generate a list of smoke co alarms."""
        return self._devices("smoke_co_alarms")

    def cameras(self):
        """Generate a list of cameras."""
        return self._devices("cameras")

    def _devices(self, device_type):
        """Generate a list of Nest devices."""
        try:
            for structure in self.nest.structures:
                if structure.name not in self.local_structure:
                    _LOGGER.debug(
                        f"Ignoring structure {structure.name}, not in {self.local_structure}"
                    )
                    continue

                for device in getattr(structure, device_type, []):
                    try:
                        # Do not optimize next statement,
                        # it is here for verify Nest API permission.
                        device.name_long
                    except KeyError:
                        _LOGGER.warning(
                            f"Cannot retrieve device name for [{device.serial}], please check your Nest developer account permission settings."
                        )
                        continue
                    yield (structure, device)

        except (AuthorizationError, APIError, OSError) as err:
            _LOGGER.error(f"Connection error while accessing Nest web service: {err}")


class NestDevice(Entity):
    """Representation of a Nest device."""

    def __init__(self, structure, device):
        """Initialize the sensor."""
        super().__init__()
        self.structure = structure

        if device:
            self.device = device
            name = self.device.name_long
        else:
            self.device = structure
            name = self.structure.name

    @property
    def device_info(self):
        """Return information about the device."""
        if hasattr(self.device, "name_long"):
            name = self.device.name_long
            if self.device.is_thermostat:
                model = MODEL_THERMOSTAT
            elif self.device.is_camera:
                model = MODEL_CAMERA
            elif self.device.is_smoke_co_alarm:
                model = MODEL_PROTECT
            else:
                model = None
            sw_version = self.device.software_version
        else:
            name = self.structure.name
            model = MODEL_STRUCTURE
            sw_version = None

        device_info = {
            "identifiers": {(DOMAIN, self.device.serial)},
            "name": name,
            "manufacturer": MANUFACTURER,
            "model": model,
        }
        if sw_version is not None:
            device_info["sw_version"] = sw_version

        return device_info

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {}

        attrs[ATTR_ATTRIBUTION] = ATTRIBUTION

        return attrs

    @property
    def name(self):
        """Return the name of the nest, if any."""
        return self._name

    @property
    def should_poll(self):
        """Do not need poll thanks using Nest streaming API."""
        return False

    @property
    def unique_id(self):
        """Return unique id."""
        return self._unique_id

    async def async_added_to_hass(self):
        """Register update signal handler."""

        async def async_update_state():
            """Update device state."""
            await self.async_update_ha_state(True)

        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL_NEST_UPDATE, async_update_state)
        )


class NestWebClientDevice(NestDevice):
    """Representation of a Sony BRAVIA device."""
    def __init__(self, structure, device, client, coordinator, id):
        """Initialize device."""
        super().__init__(structure, device)
        self.client = client
        self.coordinator = coordinator
        self.id = id

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.

        Only used by the generic entity update service.
        """

        # Ignore manual update requests if the entity is disabled
        if not self.enabled:
            return

        if hasattr(self, "update"):
            await self.hass.async_add_executor_job(self.update)
        await self.coordinator.async_request_refresh()

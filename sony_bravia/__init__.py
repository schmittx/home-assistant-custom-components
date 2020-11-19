"""Support for interface with a Sony Bravia TV."""
from datetime import timedelta
import async_timeout
import asyncio
import logging
import voluptuous as vol

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .client import SonyBRAVIAClient, ClientError
from .const import (
    ATTR_APP,
    ATTR_COMMAND,
    ATTR_HOST,
    BRAVIA_CLIENT,
    BRAVIA_COORDINATOR,
    CONF_12H,
    CONF_24H,
    CONF_ENTRY_INDEX,
    CONF_EXT_SPEAKER,
    CONF_HIDDEN,
    CONF_PSK,
    CONF_SOURCE,
    CONF_SOURCE_CONFIG,
    CONF_TIME_FORMAT,
    DEFAULT_EXT_SPEAKER,
    DEFAULT_SOURCE_CONFIG,
    DEFAULT_TIME_FORMAT,
    DOMAIN,
    MANUFACTURER,
)

PLATFORMS = ["media_player", "remote"]

SOURCE_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SOURCE): cv.string,
        vol.Optional(CONF_HIDDEN, default=False): cv.boolean,
        vol.Optional(CONF_NAME): cv.string,
    }
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PSK): cv.string,
        vol.Optional(CONF_EXT_SPEAKER, default=DEFAULT_EXT_SPEAKER): cv.boolean,
        vol.Optional(CONF_SOURCE_CONFIG, default=DEFAULT_SOURCE_CONFIG): vol.All(cv.ensure_list, [SOURCE_CONFIG_SCHEMA]),
        vol.Optional(CONF_TIME_FORMAT, default=DEFAULT_TIME_FORMAT): vol.In([CONF_12H, CONF_24H]),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [DEVICE_SCHEMA],
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the HomeKit from yaml."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    current_entries = hass.config_entries.async_entries(DOMAIN)

    entries_by_host = {entry.data[CONF_HOST]: entry for entry in current_entries}

    for index, conf in enumerate(config[DOMAIN]):
        host = conf[CONF_HOST]

        if (
            host in entries_by_host
            and entries_by_host[host].source == SOURCE_IMPORT
        ):
            entry = entries_by_host[host]
            # If they alter the yaml config we import the changes
            # since there currently is no practical way to support
            # all the options in the UI at this time.
            data = conf.copy()
#            options = {}
#            for key in CONFIG_OPTIONS:
#                options[key] = data[key]
#                del data[key]

            hass.config_entries.async_update_entry(entry, data=data)
            continue

        conf[CONF_ENTRY_INDEX] = index
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=conf,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up HomeKit from a config entry."""
#    _async_import_options_from_data_if_missing(hass, entry)

    conf = entry.data
#    options = entry.options

    client = SonyBRAVIAClient(conf[CONF_HOST], conf[CONF_PSK])

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(30):
                return await hass.async_add_executor_job(client.get_update)
        except ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name=f"Sony BRAVIA ({conf[CONF_HOST]})",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=30),
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

#    undo_listener = entry.add_update_listener(_async_update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        BRAVIA_CLIENT: client,
        BRAVIA_COORDINATOR: coordinator,
        CONF_EXT_SPEAKER: conf.get(CONF_EXT_SPEAKER, DEFAULT_EXT_SPEAKER),
        CONF_SOURCE_CONFIG: conf.get(CONF_SOURCE_CONFIG, DEFAULT_SOURCE_CONFIG),
        CONF_TIME_FORMAT: conf.get(CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT),
    }

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


#@callback
#def _async_import_options_from_data_if_missing(hass: HomeAssistant, entry: ConfigEntry):
#    options = dict(entry.options)
#    data = dict(entry.data)
#    modified = False
#    for importable_option in CONFIG_OPTIONS:
#        if importable_option not in entry.options and importable_option in entry.data:
#            options[importable_option] = entry.data[importable_option]
#            del data[importable_option]
#            modified = True

#    if modified:
#        hass.config_entries.async_update_entry(entry, data=data, options=options)


#async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
#    """Handle options update."""
#    if entry.source == SOURCE_IMPORT:
#        return
#    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class SonyBRAVIABase(CoordinatorEntity):
    """Representation of a Sony BRAVIA device."""
    def __init__(self, client, coordinator):
        """Initialize device."""
        super().__init__(coordinator)
        self.client = client
#        self._available = True
        self._cid = self.coordinator.data.get("cid")
        self._generation = self.coordinator.data.get("generation")
        self._model = self.coordinator.data.get("model")
        self._name = self.coordinator.data.get("name")

    @property
    def device_info(self):
        """Return information about the device."""
        device_info = {
            "identifiers": {(DOMAIN, self._cid)},
            "name": self._name,
            "manufacturer": MANUFACTURER,
            "model": self._model,
            "sw_version": self._generation,
        }
        return device_info

    @property
    def name(self):
        """Return the name of the entity."""
        return f"{MANUFACTURER} {self._name} {self._model}"

#    @property
#    def available(self):
#        """Return if entity is available."""
#        return self._available

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return self._unique_id

#    def update(self):
#        """Update TV info."""
#        self.client.update()
#        self._available = self.client.available

#    async def async_added_to_hass(self) -> None:
#        """Subscribe to updates."""
#        await super().async_added_to_hass()
#        self.async_on_remove(
#            self.coordinator.async_add_listener(self._async_consume_update)
#        )

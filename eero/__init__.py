"""The Eero integration."""
from datetime import timedelta
import async_timeout
import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import EeroAPI, EeroException
from .const import (
    ATTR_EERO_NAME,
    ATTR_NETWORK_NAME,
    ATTRIBUTION,
    CONF_CLIENTS,
    CONF_EEROS,
    CONF_NETWORK,
    CONF_NETWORK_NAME,
    CONF_NETWORK_URL,
    CONF_PROFILES,
    CONF_SAVE_RESPONSES,
    CONF_USER_TOKEN,
    CONF_WIRED_CLIENTS,
    CONF_WIRELESS_CLIENTS,
    DATA_COORDINATOR,
    DEFAULT_SAVE_LOCATION,
    DEFAULT_SAVE_RESPONSES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MANUFACTURER,
    MODEL_CLIENT,
    MODEL_EERO,
    MODEL_NETWORK,
    MODEL_PROFILE,
    SERVICE_RESTART_EERO,
    UNDO_UPDATE_LISTENER,
)

RESTART_EERO_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_EERO_NAME, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_NETWORK_NAME): cv.string,
    }
)

PLATFORMS = ["binary_sensor", "device_tracker", "sensor", "switch"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Eero component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a config entry."""
    hass.data.setdefault(DOMAIN, {})
    conf = entry.data
    options = entry.options

    conf_save_responses = options.get(CONF_SAVE_RESPONSES, DEFAULT_SAVE_RESPONSES)
    conf_scan_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    conf_save_location = DEFAULT_SAVE_LOCATION if conf_save_responses else None

    api = EeroAPI(user_token=conf[CONF_USER_TOKEN], network_url=conf[CONF_NETWORK_URL], save_location=conf_save_location)

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                return await hass.async_add_executor_job(api.update)
        except EeroException as exception:
            raise UpdateFailed(f"Error communicating with API: {exception.error_message}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name=f"Eero ({conf[CONF_NETWORK_NAME]})",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=conf_scan_interval),
    )
    undo_listener = entry.add_update_listener(_async_update_listener)

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    for network in coordinator.data.networks:
        if network.url == conf[CONF_NETWORK_URL]:
            conf_network = network

    all_eeros = [eero.name for eero in conf_network.eeros]
    conf_eeros = options.get(CONF_EEROS, all_eeros)
    valid_eeros = [eero for eero in conf_network.eeros if eero.name in conf_eeros]

    all_profiles = [profile.name for profile in conf_network.profiles]
    conf_profiles = options.get(CONF_PROFILES, all_profiles)
    valid_profiles = [profile for profile in conf_network.profiles if profile.name in conf_profiles]

    conf_clients = options.get(CONF_WIRED_CLIENTS, []) + options.get(CONF_WIRELESS_CLIENTS, [])
    valid_clients = [client for client in conf_network.clients if client.name_mac in conf_clients]

    valid_identifiers = [(DOMAIN, resource.id) for resource in [conf_network] + valid_eeros + valid_profiles + valid_clients]

    device_registry = await hass.helpers.device_registry.async_get_registry()
    for device_entry in hass.helpers.device_registry.async_entries_for_config_entry(device_registry, entry.entry_id):
        if all([bool(id not in valid_identifiers) for id in device_entry.identifiers]):
            device_registry.async_remove_device(device_entry.id)

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_NETWORK: conf_network,
        CONF_EEROS: valid_eeros,
        CONF_PROFILES: valid_profiles,
        CONF_CLIENTS: valid_clients,
        DATA_COORDINATOR: coordinator,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    def validate_eeros(target_eeros, target_network):
        validated_eeros = []
        for network in coordinator.data.networks:
            if network.name.lower() == target_network.lower():
                if target_eeros:
                    target_eeros = [eero.lower() for eero in target_eeros]
                    validated_eeros = [eero for eero in network.eeros if eero.name.lower() in target_eeros]
                else:
                    validated_eeros = [eero for eero in network.eeros]
        return validated_eeros

    def restart_eero(service):
        """Set the away mode for a Nest structure."""
        target_eeros = service.data[ATTR_EERO_NAME]
        target_network = service.data[ATTR_NETWORK_NAME]
        for eero in validate_eeros(target_eeros, target_network):
            eero.reboot()

    hass.services.async_register(
        DOMAIN, SERVICE_RESTART_EERO, restart_eero, schema=RESTART_EERO_SCHEMA,
    )

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class EeroEntity(CoordinatorEntity):
    """Representation of a Eero entity."""
    def __init__(self, coordinator, network_id, resource_id, variable):
        """Initialize device."""
        super().__init__(coordinator)
        self.network_id = network_id
        self.resource_id = resource_id
        self.variable = variable

    @property
    def network(self):
        """Return the state attributes."""
        for network in self.coordinator.data.networks:
            if network.id == self.network_id:
                return network

    @property
    def resource(self):
        """Return the state attributes."""
        if self.resource_id:
            for resource in self.network.resources:
                if resource.id == self.resource_id:
                    return resource
        return self.network

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        if self.resource.is_network:
            return f"{self.network.id}-{self.variable}"
        return f"{self.network.id}-{self.resource.id}-{self.variable}"

    @property
    def device_info(self):
        """Return information about the device."""
        name = self.resource.name
        if self.resource.is_network:
            model = MODEL_NETWORK
        elif self.resource.is_eero:
            model = self.resource.model
        elif self.resource.is_profile:
            model = MODEL_PROFILE
        elif self.resource.is_client:
            model = MODEL_CLIENT
            name = self.resource.name_connection_type

        device_info = {
            "identifiers": {(DOMAIN, self.resource.id)},
            "name": name,
            "manufacturer": MANUFACTURER,
            "model": model,
        }
        if hasattr(self.resource, "os_version"):
            device_info["sw_version"] = self.resource.os_version
        if any(
            [
                self.resource.is_eero,
                self.resource.is_profile,
                self.resource.is_client,
            ]
        ):
            device_info["via_device"] = (DOMAIN, self.network.id)

        return device_info

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_ATTRIBUTION: ATTRIBUTION
        }
        return attrs

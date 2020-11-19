"""The Eero integration."""
from datetime import timedelta
import async_timeout
import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, ATTR_MODE, CONF_NAME, CONF_SCAN_INTERVAL
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
    ATTR_DNS_CACHING_ENABLED,
    ATTR_IPV6_ENABLED,
    ATTR_THREAD_ENABLED,
    ATTR_EERO_NAME,
    ATTR_NETWORK_NAME,
    ATTR_TIME_OFF,
    ATTR_TIME_ON,
    ATTRIBUTION,
    CONF_CLIENTS,
    CONF_EEROS,
    CONF_NETWORKS,
    CONF_PROFILES,
    CONF_SAVE_RESPONSES,
    CONF_TIMEOUT,
    CONF_USER_TOKEN,
    CONF_WIRED_CLIENTS,
    CONF_WIRELESS_CLIENTS,
    DATA_COORDINATOR,
    DEFAULT_SAVE_LOCATION,
    DEFAULT_SAVE_RESPONSES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    ERROR_TIME_FORMAT,
    MANUFACTURER,
    MODEL_CLIENT,
    MODEL_EERO,
    MODEL_NETWORK,
    MODEL_PROFILE,
    NIGHTLIGHT_MODE_AMBIENT,
    NIGHTLIGHT_MODE_DISABLED,
    NIGHTLIGHT_MODE_SCHEDULE,
    NIGHTLIGHT_MODES,
    SERVICE_ENABLE_DNS_CACHING,
    SERVICE_ENABLE_IPV6,
    SERVICE_ENABLE_THREAD,
    SERVICE_RESTART_EERO,
    SERVICE_RESTART_NETWORK,
    SERVICE_SET_NIGHTLIGHT_MODE,
    UNDO_UPDATE_LISTENER,
)
from .util import validate_time_format

ENABLE_DNS_CACHING_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DNS_CACHING_ENABLED): cv.boolean,
        vol.Optional(ATTR_NETWORK_NAME, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)

ENABLE_IPV6_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IPV6_ENABLED): cv.boolean,
        vol.Optional(ATTR_NETWORK_NAME, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)

ENABLE_THREAD_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_THREAD_ENABLED): cv.boolean,
        vol.Optional(ATTR_NETWORK_NAME, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)

RESTART_EERO_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_EERO_NAME, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_NETWORK_NAME, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)

RESTART_NETWORK_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_NETWORK_NAME, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)

SET_NIGHTLIGHT_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MODE): vol.In(NIGHTLIGHT_MODES),
        vol.Optional(ATTR_TIME_ON): validate_time_format,
        vol.Optional(ATTR_TIME_OFF): validate_time_format,
        vol.Optional(ATTR_EERO_NAME, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_NETWORK_NAME, default=[]): vol.All(cv.ensure_list, [cv.string]),
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

    data = entry.data
    options = entry.options

    conf_save_responses = options.get(CONF_SAVE_RESPONSES, DEFAULT_SAVE_RESPONSES)
    conf_scan_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    conf_timeout = options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

    conf_save_location = DEFAULT_SAVE_LOCATION if conf_save_responses else None

    api = EeroAPI(user_token=data[CONF_USER_TOKEN], save_location=conf_save_location)

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with async_timeout.timeout(conf_timeout):
                return await hass.async_add_executor_job(api.update)
        except EeroException as exception:
            raise UpdateFailed(f"Error communicating with API: {exception.error_message}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Eero ({data[CONF_NAME]})",
        update_method=async_update_data,
        update_interval=timedelta(seconds=conf_scan_interval),
    )
    await coordinator.async_refresh()

    conf_networks = options.get(CONF_NETWORKS, data[CONF_NETWORKS])
    conf_eeros = options.get(CONF_EEROS, data.get(CONF_EEROS, []))
    conf_profiles = options.get(CONF_PROFILES, data.get(CONF_PROFILES, []))
    conf_wired_clients = options.get(CONF_WIRED_CLIENTS, data.get(CONF_WIRED_CLIENTS, []))
    conf_wireless_clients = options.get(CONF_WIRELESS_CLIENTS, data.get(CONF_WIRELESS_CLIENTS, []))
    conf_clients = conf_wired_clients + conf_wireless_clients
    if not conf_networks:
        conf_eeros = conf_profiles = conf_clients = []
    conf_identifiers = [(DOMAIN, id) for id in conf_networks + conf_eeros + conf_profiles + conf_clients]

    device_registry = await hass.helpers.device_registry.async_get_registry()
    for device_entry in hass.helpers.device_registry.async_entries_for_config_entry(device_registry, entry.entry_id):
        if all([bool(id not in conf_identifiers) for id in device_entry.identifiers]):
            device_registry.async_remove_device(device_entry.id)

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_NETWORKS: conf_networks,
        CONF_EEROS: conf_eeros,
        CONF_PROFILES: conf_profiles,
        CONF_CLIENTS: conf_clients,
        DATA_COORDINATOR: coordinator,
        UNDO_UPDATE_LISTENER: entry.add_update_listener(async_update_listener),
    }

    def enable_dns_caching(service):
        _enable_network_attribute(
            network_name=service.data[ATTR_NETWORK_NAME],
            attribute="dns_caching",
            enabled=service.data[ATTR_DNS_CACHING_ENABLED],
        )

    def enable_ipv6(service):
        _enable_network_attribute(
            network_name=service.data[ATTR_NETWORK_NAME],
            attribute="ipv6",
            enabled=service.data[ATTR_IPV6_ENABLED],
        )

    def enable_thread(service):
        _enable_network_attribute(
            network_name=service.data[ATTR_NETWORK_NAME],
            attribute="thread",
            enabled=service.data[ATTR_THREAD_ENABLED],
        )

    def restart_eero(service):
        target_eeros = [eero.lower() for eero in service.data[ATTR_EERO_NAME]]
        target_networks = [network.lower() for network in service.data[ATTR_NETWORK_NAME]]
        for eero in _validate_eeros(target_eeros, target_networks):
            eero.reboot()

    def restart_network(service):
        target_networks = [network.lower() for network in service.data[ATTR_NETWORK_NAME]]
        for network in coordinator.data.networks:
            if target_networks:
                if network.name.lower() in target_networks:
                    network.reboot()
            else:
                network.reboot()

    async def async_set_nightlight_mode(service):
        mode = service.data[ATTR_MODE]
        target_eeros = [eero.lower() for eero in service.data[ATTR_EERO_NAME]]
        target_networks = [network.lower() for network in service.data[ATTR_NETWORK_NAME]]
        for eero in _validate_eeros(target_eeros, target_networks):
            if eero.is_beacon:
                if mode == NIGHTLIGHT_MODE_DISABLED:
                    await hass.async_add_executor_job(eero.set_nightlight_disabled)
                elif mode == NIGHTLIGHT_MODE_AMBIENT:
                    await hass.async_add_executor_job(eero.set_nightlight_ambient)
                elif mode == NIGHTLIGHT_MODE_SCHEDULE:
                    on = service.data.get(ATTR_TIME_ON, eero.nightlight_schedule[0])
                    off = service.data.get(ATTR_TIME_OFF, eero.nightlight_schedule[1])
                    if on == off:
                        return
                    await hass.async_add_executor_job(eero.set_nightlight_schedule, on, off)
        await coordinator.async_request_refresh()

    def _enable_network_attribute(network_name, attribute, enabled):
        target_networks = [network.lower() for network in network_name]
        for network in coordinator.data.networks:
            if target_networks:
                if network.name.lower() in target_networks:
                    setattr(network, attribute, enabled)
            else:
                setattr(network, attribute, enabled)

    def _validate_eeros(target_eeros, target_networks):
        validated_eeros = []
        for network in coordinator.data.networks:
            if target_networks:
                if network.name.lower() in target_networks:
                    for eero in network.eeros:
                        if target_eeros:
                            if eero.name.lower() in target_eeros:
                                validated_eeros.append(eero)
                        else:
                            validated_eeros.append(eero)
            else:
                for eero in network.eeros:
                    if target_eeros:
                        if eero.name.lower() in target_eeros:
                            validated_eeros.append(eero)
                    else:
                        validated_eeros.append(eero)
        return validated_eeros

    if conf_networks:
        hass.services.async_register(
            DOMAIN,
            SERVICE_ENABLE_DNS_CACHING,
            enable_dns_caching,
            schema=ENABLE_DNS_CACHING_SCHEMA,
        )

        hass.services.async_register(
            DOMAIN,
            SERVICE_ENABLE_IPV6,
            enable_ipv6,
            schema=ENABLE_IPV6_SCHEMA,
        )

        hass.services.async_register(
            DOMAIN,
            SERVICE_ENABLE_THREAD,
            enable_thread,
            schema=ENABLE_THREAD_SCHEMA,
        )

        hass.services.async_register(
            DOMAIN,
            SERVICE_RESTART_NETWORK,
            restart_network,
            schema=RESTART_NETWORK_SCHEMA,
        )

    if conf_eeros:
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESTART_EERO,
            restart_eero,
            schema=RESTART_EERO_SCHEMA,
        )

        if any([eero.is_beacon for network in coordinator.data.networks for eero in network.eeros]):
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_NIGHTLIGHT_MODE,
                async_set_nightlight_mode,
                schema=SET_NIGHTLIGHT_MODE_SCHEMA,
            )

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


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


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class EeroEntity(CoordinatorEntity):
    """Representation of a Eero entity."""
    def __init__(self, coordinator, network, resource, variable):
        """Initialize device."""
        super().__init__(coordinator)
        self._network = network
        self._resource = resource
        self.variable = variable

    @property
    def network(self):
        """Return the state attributes."""
        for network in self.coordinator.data.networks:
            if network.id == self._network.id:
                return network

    @property
    def resource(self):
        """Return the state attributes."""
        if self._resource:
            for resource in self.network.resources:
                if resource.id == self._resource.id:
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

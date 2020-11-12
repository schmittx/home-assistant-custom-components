"""Adds config flow for Eero integration."""

import logging

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .api import EeroAPI, EeroException
from .const import (
    CONF_CODE,
    CONF_EEROS,
    CONF_LOGIN,
    CONF_NETWORK_NAME,
    CONF_NETWORK_URL,
    CONF_PROFILES,
    CONF_SAVE_RESPONSES,
    CONF_USER_TOKEN,
    CONF_WIRED_CLIENTS,
    CONF_WIRELESS_CLIENTS,
    DEFAULT_SAVE_RESPONSES,
    DEFAULT_SCAN_INTERVAL,
    DATA_COORDINATOR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class EeroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eero integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self.api = None
        self.response = None
        self.user_token = None

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            self.api = EeroAPI()

            try:
                self.response = await self.hass.async_add_executor_job(
                    self.api.login, user_input[CONF_LOGIN],
                )
            except EeroException as exception:
                _LOGGER.error(f"Status: {exception.status}, Error Message: {exception.error_message}")
                errors["base"] = "invalid_login"

            self.user_token = self.response["user_token"]

            return await self.async_step_verify()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_LOGIN, default=""): cv.string}),
            errors=errors,
        )

    async def async_step_verify(self, user_input=None):
        errors = {}

        if user_input is not None:

            try:
                self.response = await self.hass.async_add_executor_job(
                    self.api.login_verify, user_input[CONF_CODE],
                )
            except EeroException as exception:
                _LOGGER.error(f"Status: {exception.status}, Error Message: {exception.error_message}")
                errors["base"] = "invalid_code"

            return await self.async_step_network()

        return self.async_show_form(
            step_id="verify",
            data_schema=vol.Schema({vol.Required(CONF_CODE, default=""): cv.string}),
            errors=errors,
        )

    async def async_step_network(self, user_input=None):
        errors = {}

        all_networks = {}
        for network in self.response["networks"]["data"]:
            all_networks[network["name"]] = network["url"]
        valid_networks = sorted([*all_networks])

        if user_input is not None:
            uid = self.response["log_id"].lower()
            network_url = all_networks[user_input[CONF_NETWORK_NAME]]
            network_id = self.api.parse_network_id(network_url)

            await self.async_set_unique_id(f"{uid}-{network_id}")
            self._abort_if_unique_id_configured()

            user_input[CONF_USER_TOKEN] = self.user_token
            user_input[CONF_NETWORK_URL] = network_url

            return self.async_create_entry(title=f"{user_input[CONF_NETWORK_NAME]}", data=user_input)

        return self.async_show_form(
            step_id="network",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NETWORK_NAME, default=valid_networks[0]): vol.In(valid_networks),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Eero options callback."""
        return EeroOptionsFlowHandler(config_entry)


class EeroOptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options for Eero."""

    def __init__(self, config_entry):
        """Initialize Eero options flow."""
        self.config_entry = config_entry
        self.coordinator = None
        self.network = None

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        self.coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id][DATA_COORDINATOR]
        for network in self.coordinator.data.networks:
            if network.url == self.config_entry.data[CONF_NETWORK_URL]:
                self.network = network
        return await self.async_step_resources()

    async def async_step_resources(self, user_input=None):
        """Handle a flow initialized by the user."""
        all_eeros = [eero.name for eero in self.network.eeros]
        all_profiles = [profile.name for profile in self.network.profiles]
        all_wired_clients = [client.name_mac for client in self.network.clients if not client.wireless]
        all_wireless_clients = [client.name_mac for client in self.network.clients if client.wireless]

        conf_eeros = self.config_entry.options.get(CONF_EEROS, all_eeros)
        conf_profiles = self.config_entry.options.get(CONF_PROFILES, all_profiles)
        conf_wired_clients = self.config_entry.options.get(CONF_WIRED_CLIENTS, [])
        conf_wireless_clients = self.config_entry.options.get(CONF_WIRELESS_CLIENTS, [])

        default_save_responses = self.config_entry.options.get(CONF_SAVE_RESPONSES, DEFAULT_SAVE_RESPONSES)
        default_scan_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        default_eeros = [eero for eero in conf_eeros if eero in all_eeros]
        default_eeros = [eero for eero in conf_eeros if eero in all_eeros]
        default_profiles = [profile for profile in conf_profiles if profile in all_profiles]
        default_wired_clients = [client for client in conf_wired_clients if client in all_wired_clients]
        default_wireless_clients = [client for client in conf_wireless_clients if client in all_wireless_clients]

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="resources",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SAVE_RESPONSES, default=default_save_responses): cv.boolean,
                    vol.Optional(CONF_SCAN_INTERVAL, default=default_scan_interval): vol.In([30, 60, 90, 120, 300]),
                    vol.Optional(CONF_EEROS, default=default_eeros): cv.multi_select(sorted(all_eeros)),
                    vol.Optional(CONF_PROFILES, default=default_profiles): cv.multi_select(sorted(all_profiles)),
                    vol.Optional(CONF_WIRED_CLIENTS, default=default_wired_clients): cv.multi_select(sorted(all_wired_clients)),
                    vol.Optional(CONF_WIRELESS_CLIENTS, default=default_wireless_clients): cv.multi_select(sorted(all_wireless_clients)),
                }
            ),
        )

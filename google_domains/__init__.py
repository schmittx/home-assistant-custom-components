"""Support for Google Domains."""
import asyncio
from datetime import timedelta
import logging

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DOMAIN,
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_TIMEOUT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_INTERVAL,
    DEFAULT_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    EVENT_GOOGLE_DOMAINS_ENTRY_UPDATED,
    UNDO_UPDATE_INTERVAL,
    UNDO_UPDATE_LISTENER,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Initialize the Google Domains component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a config entry."""
    hass.data.setdefault(DOMAIN, {})

    domain = entry.data[CONF_DOMAIN]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    interval = entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
    timeout = entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

    session = hass.helpers.aiohttp_client.async_get_clientsession()

    result = await _update_google_domains(
        hass, session, domain, username, password, timeout
    )

    if not result:
        return False

    async def update_domain_interval(now):
        """Update the Google Domains entry."""
        await _update_google_domains(hass, session, domain, username, password, timeout)

    undo_update_interval = async_track_time_interval(hass, update_domain_interval, timedelta(minutes=interval))
    undo_update_listener = entry.add_update_listener(update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        UNDO_UPDATE_INTERVAL: undo_update_interval,
        UNDO_UPDATE_LISTENER: undo_update_listener,
    }

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_INTERVAL]()
    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()
    hass.data[DOMAIN].pop(entry.entry_id)

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _update_google_domains(hass, session, domain, username, password, timeout):
    """Update Google Domains."""
    url = f"https://{username}:{password}@domains.google.com/nic/update"

    params = {"hostname": domain}

    try:
        with async_timeout.timeout(timeout):
            resp = await session.get(url, params=params)
            body = await resp.text()

            if body.startswith("good") or body.startswith("nochg"):
                hass.bus.fire(
                    EVENT_GOOGLE_DOMAINS_ENTRY_UPDATED,
                    {CONF_DOMAIN: domain, CONF_IP_ADDRESS: body.split(" ")[1]},
                )
                return True

            _LOGGER.warning("Updating Google Domains failed: %s => %s", domain, body)

    except aiohttp.ClientError:
        _LOGGER.warning("Can't connect to Google Domains API")

    except asyncio.TimeoutError:
        _LOGGER.warning("Timeout from Google Domains API for domain: %s", domain)

    return False

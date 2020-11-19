"""Custom Component"""

"""Support for Nest Cameras."""
from datetime import timedelta
import logging

from PIL import Image
import requests
import urllib

from homeassistant.components.camera import (
    PLATFORM_SCHEMA,
    SUPPORT_ON_OFF,
    SUPPORT_STREAM,
    Camera,
)
from homeassistant.const import CONF_URL
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util.dt import utcnow

from . import NestDevice
from .const import (
    ATTR_ACTIVITY_DETECTED,
    ATTR_MOTION_DETECTED,
    ATTR_ONLINE,
    ATTR_PERSON_DETECTED,
    ATTR_SOUND_DETECTED,
    ATTR_STREAMING,
    CAMERA_OFF_IMAGE_4_3,
    CAMERA_OFF_IMAGE_16_9,
    CONF_CAMERA,
    CONF_STREAM_SOURCE,
    DATA_CONFIG,
    DATA_NEST,
    DOMAIN as NEST_DOMAIN,
    MANUFACTURER,
    SIGNAL_NEST_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up a Nest Cam.

    No longer in use.
    """


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up a Nest sensor based on a config entry."""
    nest = hass.data[NEST_DOMAIN][DATA_NEST]
    stream_source = hass.data[NEST_DOMAIN][DATA_CONFIG][CONF_STREAM_SOURCE]

    def get_cameras():
        """Get the Nest cameras."""
        cameras = []

        for structure, device in nest.cameras():
            stream_url = None
            for conf in stream_source:
                if conf[CONF_CAMERA] == device.name:
                    stream_url = conf[CONF_URL]
            cameras.append(
                NestCamera(structure, device, stream_url))

        return cameras

    async_add_entities(await hass.async_add_job(get_cameras), True)


class NestCamera(NestDevice, Camera):
    """Representation of a Nest Camera."""

    def __init__(self, structure, device, stream_url):
        """Initialize a Nest Camera."""
        super().__init__(structure, device)

        self._name = self.device.name

        self._unique_id = self.device.serial

        self._location = None
        self._online = None
        self._is_streaming = None
        self._is_video_history_enabled = False
        # Default to non-NestAware subscribed, but will be fixed during update
        self._time_between_snapshots = timedelta(seconds=30)
        self._last_image = None
        self._next_snapshot_at = None

        self._online = None
        self._motion_detected = None
        self._person_detected = None
        self._sound_detected = None
        self._activity_zones = {}
        self._activity_detected = {}
        for zone in self.device.activity_zones:
            self._activity_zones[zone.zone_id] = zone.name.lower()
            self._activity_detected[zone.zone_id] = None
        self._problem_detected = None

        self._app_url = None
        self._public_image_url = None
        self._web_url = None

        self._camera_default_image = None

        self._stream_source = stream_url

    @property
    def should_poll(self):
        """Nest camera should poll periodically."""
        return True

    @property
    def is_recording(self):
        """Return true if the device is recording."""
        return self._problem_detected

    @property
    def brand(self):
        """Return the brand of the camera."""
        return MANUFACTURER

    @property
    def supported_features(self):
        """Nest Cam support turn on and off."""
        if self._stream_source:
            return SUPPORT_ON_OFF | SUPPORT_STREAM
        return SUPPORT_ON_OFF

    @property
    def is_on(self):
        """Return true if on."""
        return self._online

    def turn_off(self):
        """Turn off camera."""
        _LOGGER.debug(f"Turn off camera {self._name}")
        # Calling Nest API in is_streaming setter.
        # device.is_streaming would not immediately change until the process
        # finished in Nest Cam.
        self.device.is_streaming = False

    def turn_on(self):
        """Turn on camera."""
        if not self._online:
            _LOGGER.error(f"Camera {self._name} is offline")
            return

        _LOGGER.debug(f"Turn on camera {self._name}")
        # Calling Nest API in is_streaming setter.
        # device.is_streaming would not immediately change until the process
        # finished in Nest Cam.
        self.device.is_streaming = True

    def update(self):
        """Cache value from Python-nest."""
        self._location = self.device.where
        self._online = self.device.online
        self._is_streaming = self.device.is_streaming
        self._is_video_history_enabled = self.device.is_video_history_enabled

        self._online = getattr(self.device, ATTR_ONLINE)
        self._motion_detected = getattr(self.device, ATTR_MOTION_DETECTED)
        self._person_detected = getattr(self.device, ATTR_PERSON_DETECTED)
        self._sound_detected = getattr(self.device, ATTR_SOUND_DETECTED)
        for zone_id, zone_name in self._activity_zones.items():
            self._activity_detected[zone_id] = bool(self.device.has_ongoing_motion_in_zone(zone_id))
        self._problem_detected = any(
            [
                bool(self._motion_detected),
                bool(self._person_detected),
                bool(self._sound_detected),
                any(self._activity_detected.values()),
            ]
        )

        self._app_url = self.device.app_url
        self._public_share_url = self.device.public_share_url
        self._web_url = self.device.web_url

        if self._is_video_history_enabled:
            # NestAware allowed 10/min
            self._time_between_snapshots = timedelta(seconds=6)
        else:
            # Otherwise, 2/min
            self._time_between_snapshots = timedelta(seconds=30)

    @property
    def state_attributes(self):
        attrs = super().state_attributes

        attrs[ATTR_ONLINE] = self._online
        attrs[ATTR_STREAMING] = self._is_streaming
        attrs[ATTR_MOTION_DETECTED] = self._motion_detected
        attrs[ATTR_PERSON_DETECTED] = self._person_detected
        attrs[ATTR_SOUND_DETECTED] = self._sound_detected
        for zone_id, zone_name in self._activity_zones.items():
            attrs[f"{zone_name}_{ATTR_ACTIVITY_DETECTED}"] = self._activity_detected[zone_id]

        return attrs

    @property
    def snapshot_url(self):
        return self.device.snapshot_url

    def _ready_for_snapshot(self, now):
        return self._next_snapshot_at is None or now > self._next_snapshot_at

    def _get_camera_default_image(self):
        url = self.device.last_event.image_url
        width, height = Image.open(urllib.request.urlopen(url)).size
        if (width / height) == (4 / 3):
            return CAMERA_OFF_IMAGE_4_3
        else:
            return CAMERA_OFF_IMAGE_16_9

    def camera_image(self):
        """Return a still image response from the camera."""
        if self._is_streaming:
            now = utcnow()
            if self._ready_for_snapshot(now):
                url = self.device.snapshot_url

                try:
                    response = requests.get(url)
                except requests.exceptions.RequestException as error:
                    _LOGGER.error(f"Error getting camera image: {error}")
                    return None

                self._next_snapshot_at = now + self._time_between_snapshots
                self._last_image = response.content
        else:
            _LOGGER.debug(f"{self.name} is not streaming, using default image")
            if self._camera_default_image is None:
                self._camera_default_image = self._get_camera_default_image()
            try:
                self._last_image = open(self._camera_default_image, "rb").read()
            except FileNotFoundError:
                _LOGGER.warning("Could not read default image from file")

        return self._last_image

    async def stream_source(self):
        """Return the source of the stream."""
        return self._stream_source

"""
Support for interface with a Sony Bravia TV.

For more details about this platform, please refer to the documentation at
https://github.com/custom-components/media_player.braviatv_psk
"""
import logging
import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    PLATFORM_SCHEMA,
    DEVICE_CLASS_TV,
    DOMAIN as DOMAIN_MEDIA_PLAYER,
)
from homeassistant.components.media_player.const import (
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_TURN_ON,
    SUPPORT_TURN_OFF,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_PLAY,
    SUPPORT_VOLUME_STEP,
    SUPPORT_VOLUME_SET,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_STOP,
    MEDIA_TYPE_APP,
    MEDIA_TYPE_TVSHOW,
    MEDIA_TYPE_VIDEO,
)
from homeassistant.const import (
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.helpers import config_validation as cv, entity_platform, service

from . import SonyBRAVIABase
from .client import TV_FORMATS
from .const import (
    ATTR_APP,
    ATTR_APP_LIST,
    ATTR_COMMAND,
    ATTR_COMMAND_LIST,
    BRAVIA_CLIENT,
    BRAVIA_COORDINATOR,
    CONF_12H,
    CONF_EXT_SPEAKER,
    CONF_HIDDEN,
    CONF_SOURCE,
    CONF_SOURCE_CONFIG,
    CONF_TIME_FORMAT,
    DOMAIN,
    SERVICE_OPEN_APP,
    SERVICE_SEND_COMMAND,
    SOURCE_APP,
    STATE_ACTIVE,
)

_LOGGER = logging.getLogger(__name__)

SUPPORTED_FEATURES = (
    SUPPORT_PAUSE |
    SUPPORT_VOLUME_STEP |
    SUPPORT_VOLUME_MUTE |
    SUPPORT_VOLUME_SET |
    SUPPORT_PREVIOUS_TRACK |
    SUPPORT_NEXT_TRACK |
    SUPPORT_TURN_ON |
    SUPPORT_TURN_OFF |
    SUPPORT_SELECT_SOURCE |
    SUPPORT_PLAY |
    SUPPORT_STOP
)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Nest device sensors based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]

    client = data.get(BRAVIA_CLIENT)
    coordinator = data.get(BRAVIA_COORDINATOR)
    ext_speaker = data.get(CONF_EXT_SPEAKER)
    source_config = data.get(CONF_SOURCE_CONFIG)
    time_format = data.get(CONF_TIME_FORMAT)

    device = SonyBRAVIATelevision(client, coordinator, ext_speaker, source_config, time_format)

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_OPEN_APP,
        {
            vol.Required(ATTR_APP): cv.string,
        },
        "open_app",
    )

    platform.async_register_entity_service(
        SERVICE_SEND_COMMAND,
        {
            vol.Required(ATTR_COMMAND): cv.string,
        },
        "send_command",
    )

    async_add_entities([device], True)


class SonyBRAVIATelevision(MediaPlayerEntity, SonyBRAVIABase):
    """Representation of a Sony TV."""

    def __init__(self, client, coordinator, ext_speaker, source_config, time_format):
        """Initialize device."""
        super().__init__(client, coordinator)

        self._ext_speaker = ext_speaker
        self._source_config = source_config
        self._time_format = time_format

        self._app_icon = None
        self._app_title = None
        self._playing = False

        self._unique_id = f"{self._cid}-{DOMAIN_MEDIA_PLAYER}"

    @property
    def _state(self):
        """Name of the current running app."""
        return self.coordinator.data.get("power_status")

    @property
    def _apps(self):
        """Name of the current running app."""
        return self.coordinator.data.get("apps", {})

    @property
    def _commands(self):
        """Name of the current running app."""
        return self.coordinator.data.get("commands", {})

    @property
    def _sources(self):
        """Name of the current running app."""
        return self._apply_source_config(self.coordinator.data.get("sources", {}))

    @property
    def _volume(self):
        """Name of the current running app."""
        return self.coordinator.data.get("volume")

    @property
    def _mute(self):
        """Name of the current running app."""
        return self.coordinator.data.get("mute")

    @property
    def _source(self):
        """Name of the current running app."""
        return self.coordinator.data.get("source")

    @property
    def _title(self):
        """Name of the current running app."""
        return self._apply_source_config_name(self.coordinator.data.get("title"))

    @property
    def _display_number(self):
        """Name of the current running app."""
        return self.coordinator.data.get("display_number")

    @property
    def _program_title(self):
        """Name of the current running app."""
        return self.coordinator.data.get("program_title")

    @property
    def _start_time(self):
        """Name of the current running app."""
        return self.coordinator.data.get("start_time")

    @property
    def _end_time(self):
        """Name of the current running app."""
        return self.coordinator.data.get("end_time")

    def _apply_source_config(self, raw_dict):
        output_dict = {}
        for source in raw_dict:
            if not self._apply_source_config_hidden(source):
                name = self._apply_source_config_name(source)
                output_dict[name] = raw_dict[source]
        return output_dict

    def _apply_source_config_hidden(self, source):
        for conf in self._source_config:
            if conf[CONF_SOURCE] == source:
                return conf[CONF_HIDDEN]
        return False

    def _apply_source_config_name(self, source):
        for conf in self._source_config:
            if conf[CONF_SOURCE] == source:
                return conf.get(CONF_NAME, source)
        return source

    def _apply_time_format(self, raw_time):
        """Convert time format."""
        if self._time_format == CONF_12H:
            hours, minutes = raw_time.split(":")
            hours, minutes = int(hours), int(minutes)
            setting = "AM"
            if hours >= 12:
                setting = "PM"
                if hours > 12:
                    hours -= 12
            elif hours == 0:
                hours = 12
            return "{}:{:02d} {}".format(hours, minutes, setting)
#            return f"{hours}:{minutes} {setting}"
        return raw_time

    def _reset_app_info(self):
        """Convert time format."""
        self._app_icon = None
        self._app_title = None

    @property
    def device_class(self):
        """Return the device class of the media player."""
        return DEVICE_CLASS_TV

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._mute

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        if self._title:
            return self._title
        return SOURCE_APP

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        if self._title:
            self._reset_app_info()
            if self._source in TV_FORMATS:
                return MEDIA_TYPE_TVSHOW
            return MEDIA_TYPE_VIDEO
        return MEDIA_TYPE_APP

    @property
    def app_id(self):
        """ID of the current running app."""
        if self._app_title:
            return self._app_title
        elif self._title:
            return None
        return SOURCE_APP

    @property
    def app_name(self):
        """Name of the current running app."""
        if self._app_title:
            return self._app_title
        elif self._title:
            return None
        return SOURCE_APP

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        return self._app_icon

    @property
    def media_series_title(self):
        """Title of series of current playing media, TV show only."""
        if self._program_title:
            if self._start_time and self._end_time:
                start_time = self._apply_time_format(self._start_time)
                end_time = self._apply_time_format(self._end_time)
                return f"{self._program_title} | {start_time} - {end_time}"
            else:
                return self._program_title
        return None

    @property
    def media_title(self):
        """Title of current playing media."""
        if self._title:
            if self._display_number:
                return f"{self._display_number}: {self._title}"
            return self._title
        return None

    @property
    def source(self):
        """Name of the current input source."""
        if self._app_title:
            return self._app_title
        if self._title:
            return self._title
        return SOURCE_APP

    @property
    def source_list(self):
        """List of available input sources."""
        return [*self._sources]

    @property
    def state(self):
        """State of the player."""
        return STATE_ON if self._state == STATE_ACTIVE else STATE_OFF

    @property
    def state_attributes(self):
        """Return the state attributes."""
        attrs = super().state_attributes

        if not attrs:
            attrs = {}

        if self._state == STATE_ACTIVE:
            if self._apps:
                attrs[ATTR_APP_LIST] = sorted(self._apps.keys())

            if self._commands:
                attrs[ATTR_COMMAND_LIST] = sorted(self._commands.keys())

        return attrs

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        if self._ext_speaker:
            return SUPPORTED_FEATURES ^ SUPPORT_VOLUME_SET
        return SUPPORTED_FEATURES

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._volume:
            return int(self._volume) / 100
        return None

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self.client.set_volume_level(volume)

    def turn_on(self):
        """Turn the media player on."""
        self.client.set_power_status(True)
#        self.client.send_command(self._commands["TvPower"])
        self._reset_app_info()

    def turn_off(self):
        """Turn the media player off."""
        self.client.set_power_status(False)
#        self.client.send_command(self._commands["TvPower"])
        self._reset_app_info()

    def volume_up(self):
        """Turn volume up for media player."""
        self.client.send_command(self._commands["VolumeUp"])

    def volume_down(self):
        """Turn volume down for media player."""
        self.client.send_command(self._commands["VolumeDown"])

    def mute_volume(self, mute):
        """Mute the volume."""
        self.client.set_audio_mute(mute)

    def select_source(self, source):
        """Select input source."""
        if source in self._sources:
            self.client.set_play_content(self._sources[source])
            self._reset_app_info()

    def media_play(self):
        """Send play command."""
        self.client.send_command(self._commands["Play"])
        self._playing = True

    def media_pause(self):
        """Send pause command."""
        command = "TvPause" if self._source in TV_FORMATS else "Pause"
        self.client.send_command(self._commands[command])
        self._playing = False

    def media_stop(self):
        """Send stop command."""
        self.client.send_command(self._commands["Stop"])
        self._playing = False

    def media_next_track(self):
        """Send next track command."""
        command = "ChannelUp" if self._source in TV_FORMATS else "Next"
        self.client.send_command(self._commands[command])

    def media_previous_track(self):
        """Send previous track command."""
        command = "ChannelDown" if self._source in TV_FORMATS else "Prev"
        self.client.send_command(self._commands[command])

    def open_app(self, app):
        """Open an app on the media player."""
        if self._state == STATE_ACTIVE and app in self._apps.keys():
            self.client.set_active_app(self._apps[app]["uri"])
            self._app_icon = self._apps[app].get("icon")
            self._app_title = app

    def send_command(self, command):
        """Send a command to the media player."""
        if command in self._commands:
            self.client.send_command(self._commands[command])

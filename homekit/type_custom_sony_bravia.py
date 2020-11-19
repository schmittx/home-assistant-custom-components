"""Custom Component"""

"""Class to hold all media player accessories."""
import logging

from pyhap.const import CATEGORY_TELEVISION

from custom_components.sony_bravia.const import (
    ATTR_COMMAND,
    DOMAIN as DOMAIN_SONY_BRAVIA,
    SERVICE_SEND_COMMAND,
)
from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN,
    SERVICE_SELECT_SOURCE,
    SUPPORT_VOLUME_SET,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PLAY_PAUSE,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    STATE_ON,
)
from homeassistant.core import callback

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_ACTIVE,
    CHAR_ACTIVE_IDENTIFIER,
    CHAR_CONFIGURED_NAME,
    CHAR_CURRENT_VISIBILITY_STATE,
    CHAR_IDENTIFIER,
    CHAR_INPUT_DEVICE_TYPE,
    CHAR_INPUT_SOURCE_TYPE,
    CHAR_IS_CONFIGURED,
    CHAR_MUTE,
    CHAR_NAME,
    CHAR_ON,
    CHAR_REMOTE_KEY,
    CHAR_SLEEP_DISCOVER_MODE,
    CHAR_VOLUME,
    CHAR_VOLUME_CONTROL_TYPE,
    CHAR_VOLUME_SELECTOR,
    CONF_INPUT_DEVICE_TYPE,
    CONF_INPUT_SOURCE_TYPE,
    CONF_SERVICE_NAME_PREFIX,
    CONF_SOURCE,
    CONF_SOURCE_CONFIG,
    DEFAULT_INPUT_DEVICE_TYPE,
    DEFAULT_INPUT_SOURCE_TYPE,
    INPUT_DEVICE_TYPES,
    INPUT_SOURCE_TYPES,
    SERV_INPUT_SOURCE,
    SERV_TELEVISION,
    SERV_TELEVISION_SPEAKER,
)

_LOGGER = logging.getLogger(__name__)

MEDIA_PLAYER_KEYS = {
    0: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Rewind"}],
    1: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Forward"}],
    2: [DOMAIN, SERVICE_MEDIA_NEXT_TRACK, {}],
    3: [DOMAIN, SERVICE_MEDIA_PREVIOUS_TRACK, {}],
    4: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Up"}],
    5: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Down"}],
    6: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Left"}],
    7: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Right"}],
    8: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Confirm"}],
    9: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Return"}],
    10: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Exit"}],
    11: [DOMAIN, SERVICE_MEDIA_PLAY_PAUSE, {}],
    15: [DOMAIN_SONY_BRAVIA, SERVICE_SEND_COMMAND, {ATTR_COMMAND: "Display"}],
}


@TYPES.register("SonyBRAVIA")
class SonyBRAVIA(HomeAccessory):
    """Generate a Sony BRAVIA accessory."""

    def __init__(self, *args):
        """Initialize a Switch accessory object."""
        super().__init__(*args, category=CATEGORY_TELEVISION)
        state = self.hass.states.get(self.entity_id)
        prefix = self.config.get(CONF_SERVICE_NAME_PREFIX, self.display_name)

        features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        self.sources = []
        source_list = state.attributes.get(ATTR_INPUT_SOURCE_LIST, [])
        if source_list:
            for source in source_list:
                self.sources.append(
                    {
                        CONF_SOURCE: source,
                        CONF_INPUT_DEVICE_TYPE: DEFAULT_INPUT_DEVICE_TYPE,
                        CONF_INPUT_SOURCE_TYPE: DEFAULT_INPUT_SOURCE_TYPE,
                    }.copy()
                )
        self.sources = self.config.get(CONF_SOURCE_CONFIG, self.sources)

        # Setup TV service
        self.tv_chars = [
            CHAR_ACTIVE,
            CHAR_ACTIVE_IDENTIFIER,
            CHAR_CONFIGURED_NAME,
            CHAR_REMOTE_KEY,
            CHAR_SLEEP_DISCOVER_MODE,
        ]

        serv_tv = self.add_preload_service(
            SERV_TELEVISION, self.tv_chars,
        )
        self.set_primary_service(serv_tv)

        self.char_active = serv_tv.configure_char(
            CHAR_ACTIVE, setter_callback=self.set_active,
        )

        self.char_input_source = serv_tv.configure_char(
            CHAR_ACTIVE_IDENTIFIER, setter_callback=self.set_input_source,
        )

        serv_tv.configure_char(
            CHAR_CONFIGURED_NAME, value=self.display_name,
        )

        self.char_remote_key = serv_tv.configure_char(
            CHAR_REMOTE_KEY, setter_callback=self.set_remote_key,
        )

        serv_tv.configure_char(
            CHAR_SLEEP_DISCOVER_MODE, value=True,
        )

        # Setup TV input services
        self.input_chars = [
            CHAR_CONFIGURED_NAME,
            CHAR_CURRENT_VISIBILITY_STATE,
            CHAR_IDENTIFIER,
            CHAR_INPUT_DEVICE_TYPE,
            CHAR_INPUT_SOURCE_TYPE,
            CHAR_IS_CONFIGURED,
            CHAR_NAME,
        ]

        for index, source in enumerate(self.sources):
            serv_input = self.add_preload_service(
                SERV_INPUT_SOURCE, self.input_chars,
            )
            serv_tv.add_linked_service(serv_input)

            serv_input.configure_char(
                CHAR_CONFIGURED_NAME, value=source[CONF_SOURCE],
            )

            serv_input.configure_char(
                CHAR_CURRENT_VISIBILITY_STATE, value=False,
            )

            serv_input.configure_char(
                CHAR_IDENTIFIER, value=index,
            )

            serv_input.configure_char(
                CHAR_INPUT_DEVICE_TYPE, value=INPUT_DEVICE_TYPES[source[CONF_INPUT_DEVICE_TYPE]],
            )

            serv_input.configure_char(
                CHAR_INPUT_SOURCE_TYPE, value=INPUT_SOURCE_TYPES[source[CONF_INPUT_SOURCE_TYPE]],
            )

            serv_input.configure_char(
                CHAR_IS_CONFIGURED, value=True,
            )

            serv_input.configure_char(
                CHAR_NAME, value=source[CONF_SOURCE],
            )

            _LOGGER.info("%s: Added source %s", self.entity_id, source[CONF_SOURCE])

        # Setup speaker service
        self.speaker_chars = [
            CHAR_ACTIVE,
            CHAR_MUTE,
            CHAR_NAME,
            CHAR_VOLUME_CONTROL_TYPE,
            CHAR_VOLUME_SELECTOR,
        ]
        if features & SUPPORT_VOLUME_SET:
            self.speaker_chars.append(CHAR_VOLUME)

        serv_speaker = self.add_preload_service(
            SERV_TELEVISION_SPEAKER, self.speaker_chars,
        )
        serv_tv.add_linked_service(serv_speaker)

        serv_speaker.configure_char(
            CHAR_ACTIVE, value=1,
        )

        self.char_mute = serv_speaker.configure_char(
            CHAR_MUTE, value=False, setter_callback=self.set_mute,
        )

        serv_speaker.configure_char(
            CHAR_NAME, value=f"{self.display_name} Volume",
        )

        volume_control_type = 1 if CHAR_VOLUME in self.speaker_chars else 2
        serv_speaker.configure_char(
            CHAR_VOLUME_CONTROL_TYPE, value=volume_control_type,
        )

        self.char_volume_selector = serv_speaker.configure_char(
            CHAR_VOLUME_SELECTOR, setter_callback=self.set_volume_step,
        )

        if CHAR_VOLUME in self.speaker_chars:
            self.char_volume = serv_speaker.configure_char(
                CHAR_VOLUME, setter_callback=self.set_volume,
            )

        self.async_update_state(state)

    def set_active(self, value):
        """Move switch state to value if call came from HomeKit."""
        _LOGGER.debug('%s: Set switch state for "on_off" to %s', self.entity_id, value)
        service = SERVICE_TURN_ON if value else SERVICE_TURN_OFF
        params = {ATTR_ENTITY_ID: self.entity_id}
        self.call_service(DOMAIN, service, params)

    def set_input_source(self, value):
        """Send input set value if call came from HomeKit."""
        _LOGGER.debug("%s: Set current input to %s", self.entity_id, value)
        source = self.sources[value][CONF_SOURCE]
        params = {ATTR_ENTITY_ID: self.entity_id, ATTR_INPUT_SOURCE: source}
        self.call_service(DOMAIN, SERVICE_SELECT_SOURCE, params)

    def set_mute(self, value):
        """Move switch state to value if call came from HomeKit."""
        _LOGGER.debug(
            '%s: Set switch state for "toggle_mute" to %s', self.entity_id, value
        )
        params = {ATTR_ENTITY_ID: self.entity_id, ATTR_MEDIA_VOLUME_MUTED: value}
        self.call_service(DOMAIN, SERVICE_VOLUME_MUTE, params)

    def set_remote_key(self, value):
        """Send remote key value if call came from HomeKit."""
        _LOGGER.debug("%s: Set remote key to %s", self.entity_id, value)
        domain = MEDIA_PLAYER_KEYS[value][0]
        service = MEDIA_PLAYER_KEYS[value][1]
        params = MEDIA_PLAYER_KEYS[value][2]
        params.update({ATTR_ENTITY_ID: self.entity_id})
        self.call_service(domain, service, params)

    def set_volume(self, value):
        """Send volume step value if call came from HomeKit."""
        _LOGGER.debug("%s: Set volume to %s", self.entity_id, value)
        params = {ATTR_ENTITY_ID: self.entity_id, ATTR_MEDIA_VOLUME_LEVEL: value}
        self.call_service(DOMAIN, SERVICE_VOLUME_SET, params)

    def set_volume_step(self, value):
        """Send volume step value if call came from HomeKit."""
        _LOGGER.debug("%s: Step volume by %s", self.entity_id, value)
        service = SERVICE_VOLUME_DOWN if value else SERVICE_VOLUME_UP
        params = {ATTR_ENTITY_ID: self.entity_id}
        self.call_service(DOMAIN, service, params)

    @callback
    def async_update_state(self, new_state):
        """Update Television state after state changed."""

        # Handle power state
        active = 1 if new_state.state == STATE_ON else 0
        _LOGGER.debug("%s: Set current active state to %s", self.entity_id, active)
        if self.char_active.value != active:
            self.char_active.set_value(active)

        # Handle active input
        if self.sources:
            index = None
            source_name = new_state.attributes.get(ATTR_INPUT_SOURCE)
            _LOGGER.debug("%s: Set current input to %s", self.entity_id, source_name)
            for _index, source in enumerate(self.sources):
                if source_name == source[CONF_SOURCE]:
                    index = _index
                    break
            if index:
                if self.char_input_source.value != index:
                    self.char_input_source.set_value(index)
            elif active:
                _LOGGER.debug(
                    "%s: Sources out of sync. Restart Home Assistant", self.entity_id,
                )
                if self.char_input_source.value != 0:
                    self.char_input_source.set_value(0)

        # Handle mute state
        mute = bool(new_state.attributes.get(ATTR_MEDIA_VOLUME_MUTED))
        if self.char_mute.value != mute:
            self.char_mute.set_value(mute)

        # Handle volume level
        if CHAR_VOLUME in self.speaker_chars:
            volume = new_state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL)
            if isinstance(volume_level, (float, int)):
                volume = int(volume * 100)
                _LOGGER.debug("%s: Set current volume level to %s", self.entity_id, volume)
                if self.char_volume.value != volume:
                    self.char_volume.set_value(volume)

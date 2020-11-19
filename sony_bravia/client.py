"""Sony Bravia device"""
import collections
import datetime
import json
import logging
import requests
import socket
import struct
import time

EXT_INPUTS = [
    "extInput:cec",
    "extInput:component",
    "extInput:composite",
    "extInput:hdmi",
    "extInput:widi",
]
MINIMUM_UPDATE_INTERVAL = 0
TIMEOUT = 8
TV_FORMATS = [
    "tv:analog",
    "tv:atsct",
    "tv:dvbc",
    "tv:dvbs",
    "tv:dvbt",
    "tv:isdbbs",
    "tv:isdbcs",
    "tv:isdbgt",
    "tv:isdbt",
]

_LOGGER = logging.getLogger(__name__)


class ClientError(Exception):
    """Raised when an update has failed."""


class SonyBRAVIAClient(object):
    """Representation of a Sony Bravia device."""

    def __init__(self, host, psk):
        """Initialize the Sony Bravia class."""
        self._host = host
        self._psk = psk
        self._data = {}
        self._last_update_timestamp = time.time()

    def connect(self):
        """Get info on TV."""
        system_info = self.get_system_info()
        self.parse_system_info(system_info)
        self._data["available"] = True if system_info else False

        return self._data

    def _jdata_build(self, method, params):
        if params:
            ret = json.dumps(
                {"method": method, "params": [params], "id": 1, "version": "1.0"}
            )
        else:
            ret = json.dumps(
                {"method": method, "params": [], "id": 1, "version": "1.0"}
            )
        return ret

    def _send_req_ircc(self, params, log_errors=False):
        """Send an IRCC command via HTTP to Sony Bravia."""
        if params is None:
            return False
        headers = {
            "X-Auth-PSK": self._psk,
            "SOAPACTION": '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"',
        }
        data = (
            '<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org'
            + '/soap/envelope/" '
            + 's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
            + "<u:X_SendIRCC "
            + 'xmlns:u="urn:schemas-sony-com:service:IRCC:1"><IRCCCode>'
            + params
            + "</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>"
        ).encode("UTF-8")
        try:
            response = requests.post(
                "http://" + self._host + "/sony/IRCC",
                headers=headers,
                data=data,
                timeout=TIMEOUT,
            )
        except requests.exceptions.HTTPError as exception_instance:
            if log_errors:
                raise ClientError(f"HTTPError: {str(exception_instance)}")
#                _LOGGER.error(f"HTTPError: {str(exception_instance)}")

        except requests.exceptions.Timeout as exception_instance:
            if log_errors:
                raise ClientError(f"Timeout: {str(exception_instance)}")
#                _LOGGER.error(f"Timeout: {str(exception_instance)}")

        except Exception as exception_instance:
            if log_errors:
                raise ClientError(f"Exception: {str(exception_instance)}")
#                _LOGGER.warning(f"Exception: {str(exception_instance)}")
        else:
            content = response.content
            return content

    def _send_req_json(self, endpoint, params, log_errors=False):
        """Send request command via HTTP json to Sony Bravia."""
        try:
            response = requests.post(
                "http://" + self._host + "/sony/" + endpoint,
                data=params.encode("UTF-8"),
                headers={"X-Auth-PSK": self._psk},
                timeout=TIMEOUT,
            )
        except requests.exceptions.HTTPError as exception_instance:
            if log_errors:
                raise ClientError(f"HTTPError: {str(exception_instance)}")
#                _LOGGER.error(f"HTTPError: {str(exception_instance)}")

        except requests.exceptions.Timeout as exception_instance:
            if log_errors:
                raise ClientError(f"Timeout: {str(exception_instance)}")
#                _LOGGER.error(f"Timeout: {str(exception_instance)}")

        except Exception as exception_instance:
            if log_errors:
                raise ClientError(f"Exception: {str(exception_instance)}")
#                _LOGGER.error(f"Exception: {str(exception_instance)}")

        else:
            response = json.loads(response.content.decode("utf-8"))
            if "error" in response and log_errors:
                raise ClientError(f"Invalid response: {response}, request path: {endpoint}, request params: {params}")
#                _LOGGER.warning(
#                    "Invalid response: %s\n  request path: %s\n  request params: %s"
#                    % (response, endpoint, params)
#                )
            return response

        return {"error": ""}

    def parse_system_info(self, system_info):
        """Get volume info."""
        self._data["model"] = system_info.get("model")
        self._data["name"] = system_info.get("name")
        self._data["serial"] = system_info.get("serial")
        self._data["mac_address"] = system_info.get("macAddr")
        self._data["generation"] = system_info.get("generation")
        self._data["cid"] = system_info.get("cid")

    def _add_seconds(self, tm, secs):
        """Add seconds to time (HH:MM:SS)."""
        fulldate = datetime.datetime(100, 1, 1, tm.hour, tm.minute, tm.second)
        fulldate = fulldate + datetime.timedelta(seconds=secs)
        return fulldate.time()

    def set_active_app(self, uri):
        """Open app with given uri."""
        resp = self._send_req_json(
            "appControl",
            self._jdata_build("setActiveApp", {"uri": uri}),
        )
        if resp.get("error"):
            _LOGGER.error("ERROR: %s" % resp.get("error"))

    def send_command(self, ircc):
        """Send command to the TV."""
        self._send_req_ircc(ircc)

    def get_update(self):
        """Send command to the TV."""
        if time.time() - self._last_update_timestamp <= MINIMUM_UPDATE_INTERVAL:
            return self._data

        power_status = self.get_power_status()
        self._data["power_status"] = power_status
        self._data["available"] = True if power_status else False

        if any(
            [
                not self._data.get("model"),
                not self._data.get("name"),
                not self._data.get("serial"),
                not self._data.get("mac_address"),
                not self._data.get("generation"),
                not self._data.get("cid"),
            ]
        ):
            system_info = self.get_system_info()
            self.parse_system_info(system_info)

        if power_status != "active":
            self._last_update_timestamp = time.time()
            return self._data

        self._data["apps"] = self.get_apps()
        self._data["commands"] = self.get_commands()
        self._data["sources"] = self.get_sources()

        volume_info = self.get_volume_info()
        self._data["volume"] = volume_info.get("volume")
        self._data["mute"] = volume_info.get("mute")

        playing_info = self.get_playing_info()
        self._data["title"] = playing_info.get("title")
        self._data["display_number"] = playing_info.get("dispNum")
        self._data["program_title"] = playing_info.get("programTitle")
        self._data["source"] = playing_info.get("source")

        playing_time = self.get_playing_time(playing_info)
        self._data["start_time"] = playing_time.get("start_time")
        self._data["end_time"] = playing_time.get("end_time")

        self._last_update_timestamp = time.time()
        return self._data

    def get_apps(self):
        """Get the list of installed apps."""
        _apps = []
        resp = self._send_req_json(
            "appControl",
            self._jdata_build("getApplicationList", None),
        )
        if not resp.get("error"):
            _apps.extend(resp.get("result")[0])

        apps = {}
        for app in _apps:
            title = app["title"].replace("&amp;", "&")
            apps[title] = {
                "uri": app["uri"],
            }
            icon = app["icon"]
            if icon:
                apps[title]["icon"] = icon
        return apps

    def get_commands(self):
        _commands = []
        resp = self._send_req_json(
            "system",
            self._jdata_build("getRemoteControllerInfo", None),
        )
        if not resp.get("error"):
            _commands.extend(resp.get("result")[1])

        commands = {}
        for command in _commands:
            commands[command["name"]] = command["value"]
        return commands

    def get_sources(self):
        """Load source list from Sony Bravia."""
        _sources = []
        resp = self._send_req_json(
            "avContent",
            self._jdata_build("getSourceList", {"scheme": "tv"}),
        )
        if not resp.get("error"):
            results = resp.get("result")[0]
            for result in results:
                if result["source"] in TV_FORMATS:
                    resp = self._send_req_json(
                        "avContent",
                        self._jdata_build("getContentList", result),
                    )
                    if not resp.get("error"):
                        _sources.extend(resp.get("result")[0])

        resp = self._send_req_json(
            "avContent",
            self._jdata_build("getSourceList", {"scheme": "extInput"}),
        )
        if not resp.get("error"):
            results = resp.get("result")[0]
            for result in results:
                if result["source"] in EXT_INPUTS:
                    resp = self._send_req_json(
                        "avContent",
                        self._jdata_build("getContentList", result),
                    )
                    if not resp.get("error"):
                        _sources.extend(resp.get("result")[0])

        _input_labels = []
        resp = self._send_req_json(
            "avContent",
            self._jdata_build("getCurrentExternalInputsStatus", None),
        )
        if not resp.get("error"):
            _input_labels.extend(resp.get("result")[0])

        input_labels = {}
        for input in _input_labels:
            if input["label"]:
                input_labels[input["title"]] = input["label"]

        sources = {}
        for source in _sources:
            label = input_labels.get(source["title"], source["title"])
            if label:
                sources[label] = source["uri"]
        return sources

    def get_playing_info(self):
        """Get information on program that is shown on TV."""
        playing_info = {}
        resp = self._send_req_json(
            "avContent",
            self._jdata_build("getPlayingContentInfo", None),
        )
        if not resp.get("error"):
            playing_info = resp.get("result")[0]
        return playing_info

    def get_playing_time(self, playing_info):
        """Return starttime and endtime (HH:MM) of TV program."""
        # startdatetime format 2017-03-24T00:00:00+0100
        playing_time = {}
        start_date_time = playing_info.get("startDateTime")
        duration = playing_info.get("durationSec")
        if start_date_time and duration:
            start_date_time = start_date_time[:19]  # Remove timezone

            start = datetime.datetime.strptime(
                start_date_time, "%Y-%m-%dT%H:%M:%S"
            ).time()
            end = self._add_seconds(start, duration)
            start_time = start.strftime("%H:%M")
            end_time = end.strftime("%H:%M")
            playing_time = {
                "start_time": start_time,
                "end_time": end_time,
            }
        return playing_time

    def get_power_status(self):
        """Get power status being off, active or standby."""
        power_status = None
        resp = self._send_req_json(
            "system",
            self._jdata_build("getPowerStatus", None),
        )
        if not resp.get("error"):
            power_status = resp.get("result")[0].get("status")
        return power_status

    def get_volume_info(self):
        """Get volume info."""
        volume_info = {}
        resp = self._send_req_json(
            "audio",
            self._jdata_build("getVolumeInformation", None),
        )
        if not resp.get("error"):
            results = resp.get("result")[0]
            for result in results:
                if result["target"] == "speaker":
                    volume_info = result
        return volume_info

    def get_system_info(self):
        """Get info on TV."""
        system_info = {}
        resp = self._send_req_json(
            "system",
            self._jdata_build("getSystemInformation", None),
        )
        if not resp.get("error"):
            system_info = resp.get("result")[0]
        return system_info

    def set_audio_volume(self, volume):
        """Set volume level, range 0..1."""
        self._send_req_json(
            "audio",
            self._jdata_build("setAudioVolume", {"target": "speaker", "volume": str(int(round(volume * 100)))}),
        )

    def set_audio_mute(self, mute):
        """Set volume level, range 0..1."""
        self._send_req_json(
            "audio",
            self._jdata_build("setAudioMute", {"status": bool(mute)}),
        )

    def set_power_status(self, status):
        """Turn off media player using the rest-api for Android TV."""
        self._send_req_json(
            "system",
            self._jdata_build("setPowerStatus", {"status": bool(status)}),
        )

    def wol(self):
        if self.mac_address:
            addr_byte = self.mac_address.split(":")
            hw_addr = struct.pack(
                "BBBBBB",
                int(addr_byte[0], 16),
                int(addr_byte[1], 16),
                int(addr_byte[2], 16),
                int(addr_byte[3], 16),
                int(addr_byte[4], 16),
                int(addr_byte[5], 16),
            )
            msg = b"\xff" * 6 + hw_addr * 16
            socket_instance = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socket_instance.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            socket_instance.sendto(msg, ("<broadcast>", 9))
            socket_instance.close()

    def set_play_content(self, uri):
        """Play content by URI."""
        self._send_req_json(
            "avContent",
            self._jdata_build("setPlayContent", {"uri": uri}),
        )

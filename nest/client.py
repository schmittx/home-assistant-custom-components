import logging
import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from time import time

API_BASE_URL = "https://home.nest.com"

KNOWN_BUCKET_TYPES = [
    "structure",
    # Thermostat
    "device",
    # Temperature Sensor
    "kryptonite",
]
NEST_API_KEY = "AIzaSyAdkSIMNc51XGNEAYWasX9UOWkS5P6sZE4"

RETRY_BACKOFF = 0.5
RETRY_METHODS = frozenset(
    [
        "HEAD",
        "TRACE",
        "GET",
        "PUT",
        "OPTIONS",
        "DELETE",
        "POST",
    ]
)
RETRY_NUM = 5
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36"

_LOGGER = logging.getLogger(__name__)

logging.getLogger(requests.packages.urllib3.__package__).setLevel(logging.ERROR)


class ClientError(Exception):
    """Raised when an update has failed."""


class NestWebClient():
    def __init__(self, user_id, access_token, region="us"):
        self.data = {}

        self._wheres = {}
        self._user_id = user_id
        self._access_token = access_token
        self._retries = Retry(
            total=RETRY_NUM,
            backoff_factor=RETRY_BACKOFF,
            method_whitelist=RETRY_METHODS
        )
        self._adapter = HTTPAdapter(max_retries=self._retries)
        self._session = requests.Session()
        self._session.headers.update({
            "Referer": "https://home.nest.com/",
            "User-Agent": USER_AGENT,
        })
        self._session.mount("https://", self._adapter)
        self._session.mount("http://", self._adapter)
        self._czfe_url = None
        self._valid_credentials = None

        self._structures = []
        self._thermostats = []
        self._temperature_sensors = []

        self._get_data(self._launch())

    @property
    def _devices(self):
        return self._structures + self._temperature_sensors + self._thermostats

    @property
    def temperature_sensors(self):
        return self._temperature_sensors

    @property
    def _device_name_id_map(self):
        map = {}
        for device in self._devices:
            map[self.data[device]["name"]] = device
        return map

    def get_device_id(self, device_name):
        return self._device_name_id_map.get(device_name)

    def valid_device(self, device_name):
        return bool(self.get_device_id(device_name) is not None)

    @property
    def valid_credentials(self):
        """Return true if the credentials are known to be valid."""
        return bool(self._valid_credentials)

    def _launch(self):
        self._session.post(
            f"{API_BASE_URL}/dropcam/api/login",
            data={"access_token": self._access_token}
        )
        try:
            response = self._session.post(
                f"{API_BASE_URL}/api/0.1/user/{self._user_id}/app_launch",
                json={
                    "known_bucket_types": ["buckets", "structure", "where"],
                    "known_bucket_versions": [],
                },
                headers={"Authorization": f"Basic {self._access_token}"},
            )
            self._czfe_url = response.json()["service_urls"]["urls"]["czfe_url"]
            self._valid_credentials = True if response else False
            return response
        except requests.exceptions.RequestException as error:
            raise ClientError(f"Failed to launch, status code: {response.status_code}, response: {response.content}, error: {error}")
            return None

    def _get_data(self, response):
        self._get_devices(response)
        self._get_wheres(response)

    def _get_devices(self, response):
        for updated_bucket in response.json()["updated_buckets"]:
            if updated_bucket["object_key"].startswith(f"buckets."):
                for bucket in updated_bucket["value"]["buckets"]:
                    id = bucket.split(".")[1]
                    if bucket.startswith("structure."):
                        self._structures.append(id)
                        self.data[id] = {}
                    elif bucket.startswith("device."):
                        self._thermostats.append(id)
                        self.data[id] = {}
                    elif bucket.startswith("kryptonite."):
                        self._temperature_sensors.append(id)
                        self.data[id] = {}

    def _get_wheres(self, response):
        for updated_bucket in response.json()["updated_buckets"]:
            if updated_bucket["object_key"].startswith(f"where."):
                wheres = updated_bucket["value"]["wheres"]
                for where in wheres:
                    self._wheres[where["where_id"]] = where["name"]

    def get_update(self):
        try:
            response = self._session.post(
                f"{API_BASE_URL}/api/0.1/user/{self._user_id}/app_launch",
                json={
                    "known_bucket_types": KNOWN_BUCKET_TYPES,
                    "known_bucket_versions": [],
                },
                headers={"Authorization": f"Basic {self._access_token}"},
            )
            if response.status_code != 200:
                return self.data

            for bucket in response.json()["updated_buckets"]:
                sensor_data = bucket["value"]
                id = bucket["object_key"].split(".")[1]
                if bucket["object_key"].startswith(f"structure.{id}"):
                    self.data[id]["name"] = sensor_data["name"]
                else:
                    where = self._wheres[sensor_data["where_id"]]
                    self.data[id]["location"] = where

                    if bucket["object_key"].startswith(f"device.{id}"):
                        self.data[id]["name"] = f"{where} Thermostat"

                    elif bucket["object_key"].startswith(f"kryptonite.{id}"):
                        self.data[id]["name"] = f"{where} Temperature Sensor"

                    for key, value in sensor_data.items():
                        self.data[id][key] = value

            for structure, data in response.json()["weather_for_structures"].items():
                id = structure.split(".")[1]
                for bucket, measurements in data.items():
                    for variable in measurements:
                        value = measurements[variable]
                        self.data[id][variable] = float(value) if variable in ["sunrise", "sunset", "temp_c", "zip"] else value

        except requests.exceptions.RequestException as error:
            raise ClientError(f"Failed to update, status code: {response.status_code}, response: {response.content}, error: {error}")
        return self.data

    def _thermostat_set_properties(self, device_id, property, value):
        if device_id not in self._thermostats:
            return

        try:
            self._session.post(
                f"{self._czfe_url}/v5/put",
                json={
                    "objects": [
                        {
                            "object_key": f"device.{device_id}",
                            "op": "MERGE",
                            "value": {property: value},
                        }
                    ]
                },
                headers={"Authorization": f"Basic {self._access_token}"},
            )
        except requests.exceptions.RequestException as error:
            raise ClientError(f"Failed to set {property} to {value}, status code: {response.status_code}, response: {response.content}, error: {error}")
            pass

    def thermostat_set_target_humidity(self, device_id, humidity):
        self._thermostat_set_properties(device_id, "target_humidity", humidity)

    def thermostat_enable_target_humidity(self, device_id, enabled):
        self._thermostat_set_properties(device_id, "target_humidity_enabled", enabled)

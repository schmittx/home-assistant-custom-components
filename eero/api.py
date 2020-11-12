"""Eero API"""
import json
import os
import re
import requests

API_ENDPOINT = "https://api-user.e2ro.com"


class EeroException(Exception):
    def __init__(self, status, error_message):
        super(EeroException, self).__init__()
        self.status = status
        self.error_message = error_message


class EeroAPI(object):

    def __init__(self, user_token=None, network_url=None, save_location=None):
        self.data = None
        self.session = requests.Session()
        self.user_token = user_token
        self.network_url = network_url
        self.save_location = save_location

    @property
    def cookie(self):
        if self.user_token:
            return dict(s=self.user_token)
        return dict()

    def parse_response(self, response):
        data = json.loads(response.text)
        if data["meta"]["code"] not in [200, 201]:
            raise EeroException(data["meta"]["code"], data["meta"].get("error", ""))
        return data.get("data", "")

    def save_response(self, response, name="response"):
        if self.save_location and response:
            if not os.path.isdir(self.save_location):
                os.mkdir(self.save_location)
            name = name.replace("/", "_").replace(".", "_")
            with open(f"{self.save_location}/{name}.json", "w") as file:
                json.dump(response, file, indent=4)
            file.close()

    def get(self, url, **kwargs):
        response = self.refresh(lambda:
            self.session.get(f"{API_ENDPOINT}{url}", cookies=self.cookie, **kwargs)
        )
        response = self.parse_response(response)
        self.save_response(response=response, name=url)
        return response

    def post(self, url, data=None, json=None, **kwargs):
        response = self.refresh(lambda:
            self.session.post(f"{API_ENDPOINT}{url}", cookies=self.cookie, data=data, json=json, **kwargs)
        )
        response = self.parse_response(response)
        self.save_response(response=response, name=url)
        return response

    def put(self, url, data=None, **kwargs):
        response = self.refresh(lambda:
            self.session.put(f"{API_ENDPOINT}{url}", cookies=self.cookie, data=data, **kwargs)
        )
        response = self.parse_response(response)
        self.save_response(response=response, name=url)
        return response

    def login(self, login):
        response = self.post(
            url="/2.2/login",
            json=dict(login=login),
        )
        self.user_token = response["user_token"]
        return response

    def login_refresh(self):
        response = self.post(
            url="/2.2/login/refresh",
        )
        self.user_token = response["user_token"]
        return response

    def login_verify(self, code):
        response = self.post(
            url="/2.2/login/verify",
            json=dict(code=code),
        )
        return response

    def id_from_url(self, id_or_url):
        match = re.search("^[0-9]+$", id_or_url)
        if match:
            return match.group(0)
        match = re.search(r"\/([0-9]+)$", id_or_url)
        if match:
            return match.group(1)

    def parse_network_id(self, url):
        return url.replace("/2.2/networks/", "")

    def refresh(self, function):
        try:
            return function()
        except EeroException as exception:
            if (exception.status == 401 and exception.error_message == "error.session.refresh"):
                self.login_refresh()
                return function()
            else:
                raise

    def update(self):
        try:
            account = self.get(url="/2.2/account")

            if self.network_url:
                target_networks = [network for network in account["networks"]["data"] if network["url"] == self.network_url]
            else:
                target_networks = account["networks"]["data"]

            networks = list()
            for network in target_networks:
                network_data = self.get(url=network["url"])
                for resource in ["profiles", "devices"]:
                    resource_data = self.get(url=network_data["resources"][resource])
                    network_data[resource] = dict(count=len(resource_data), data=resource_data)
                networks.append(network_data)
            account["networks"]["data"] = networks
            self.data = Account(self, account)
        except EeroException as exception:
            return self.data
        return self.data


class Base(object):

    @property
    def is_account(self):
        return bool(self.__class__.__name__ in ["AccountMultiNetwork", "AccountSingleNetwork"])

    @property
    def is_network(self):
        return bool(self.__class__.__name__ == "Network")

    @property
    def is_eero(self):
        return bool(self.__class__.__name__ == "Eero")

    @property
    def is_profile(self):
        return bool(self.__class__.__name__ == "Profile")

    @property
    def is_client(self):
        return bool(self.__class__.__name__ == "Client")


class Account(Base):

    def __init__(self, api, data):
        self.api = api
        self.data = data

    @property
    def name(self):
        return self.data.get("name")

    @property
    def email(self):
        return self.data.get("email", {}).get("value")

    @property
    def phone(self):
        return self.data.get("phone", {}).get("value")

    @property
    def log_id(self):
        return self.data.get("log_id")

    @property
    def premium_status(self):
        return self.data.get("premium_status")

    @property
    def networks(self):
        networks = []
        for network in self.data.get("networks", {}).get("data", []):
            networks.append(Network(self.api, self, network))
        return networks


class Network(Base):

    def __init__(self, api, account, data):
        self.api = api
        self.account = account
        self.data = data

    @property
    def url(self):
        return self.data.get("url")

    @property
    def id(self):
        return self.url.replace("/2.2/networks/", "")

    @property
    def name(self):
        return self.data.get("name")

    @property
    def status(self):
        return self.data.get("status")

    @property
    def public_ip(self):
        return self.data.get("ip_settings", {}).get("public_ip")

    @property
    def premium_status(self):
        return self.data.get("premium_status")

    @property
    def premium_status_enabled(self):
        return bool(self.premium_status == "active")

    @property
    def ad_block(self):
        return self.data.get("premium_dns", {}).get("dns_policies", {}).get("ad_block")

    @ad_block.setter
    def ad_block(self, value):
        return self.api.post(
                url=f"/2.2/networks/{self.id}/dns_policies/network",
                json=dict(ad_block=bool(value)),
        )

    @property
    def block_malware(self):
        return self.data.get("premium_dns", {}).get("dns_policies", {}).get("block_malware")

    @block_malware.setter
    def block_malware(self, value):
        return self.api.post(
                url=f"/2.2/networks/{self.id}/dns_policies/network",
                json=dict(block_malware=bool(value)),
        )

    @property
    def speed(self):
        return (
            self.data.get("speed", {}).get("down", {}).get("value"),
            self.data.get("speed", {}).get("up", {}).get("value"),
        )

    @property
    def speed_units(self):
        return (
            self.data.get("speed", {}).get("down", {}).get("units"),
            self.data.get("speed", {}).get("up", {}).get("units"),
        )

    @property
    def speed_date(self):
        return self.data.get("speed", {}).get("date")

    @property
    def guest_network_enabled(self):
        return self.data.get("guest_network", {}).get("enabled")

    @guest_network_enabled.setter
    def guest_network_enabled(self, value):
        return self.api.put(
                url=f"/2.2/networks/{self.id}/guestnetwork",
                json=dict(enabled=bool(value)),
        )

    @property
    def guest_network_name(self):
        return self.data.get("guest_network", {}).get("name")

    @property
    def target_firmware(self):
        return self.data.get("updates", {}).get("target_firmware")

    @property
    def clients_count(self):
        return self.data.get("clients", {}).get("count")

    @property
    def health_internet_status(self):
        return self.data.get("health", {}).get("internet", {}).get("status")

    @property
    def health_internet_isp_up(self):
        return self.data.get("health", {}).get("internet", {}).get("isp_up")

    @property
    def health_eero_network_status(self):
        return self.data.get("health", {}).get("eero_network", {}).get("status")

    @property
    def timezone(self):
        return self.data.get("timezone", {}).get("value")

    @property
    def eeros(self):
        eeros = []
        for eero in self.data.get("eeros", {}).get("data", []):
            eeros.append(Eero(self.api, self.account, self, eero))
        return eeros

    @property
    def profiles(self):
        profiles = []
        for profile in self.data.get("profiles", {}).get("data", []):
            profiles.append(Profile(self.api, self.account, self, profile))
        return profiles

    @property
    def clients(self):
        clients = []
        for client in self.data.get("devices", {}).get("data", []):
            clients.append(Client(self.api, self.account, self, client))
        return clients

    @property
    def resources(self):
        return self.eeros + self.profiles + self.clients


class Eero(Base):

    def __init__(self, api, account, network, data):
        self.api = api
        self.account = account
        self.network = network
        self.data = data

    def reboot(self):
        return self.api.post(url=f"/2.2/eeros/{self.id}/reboot")

    def set_nightlight_enabled(self, value):
        return self.api.put(
                url=f"/2.2/eeros/{self.id}/nightlight/settings",
                json=dict(enabled=bool(value)),
        )

    def set_nightlight_schedule(self, time_on=None, time_off=None):
        json = dict(schedule=dict(enabled=True))
        if time_on:
            json["schedule"].update(dict(on=time_on))
        if time_off:
            json["schedule"].update(dict(off=time_off))
        return self.api.put(
                url=f"/2.2/eeros/{self.id}/nightlight/settings",
                json=json,
        )

    @property
    def url(self):
        return self.data.get("url")

    @property
    def id(self):
        return self.url.replace("/2.2/eeros/", "")

    @property
    def location(self):
        return self.data.get("location")

    @property
    def model(self):
        return self.data.get("model")

    @property
    def name(self):
        return self.location

    @property
    def os_version(self):
        return self.data.get("os_version")

    @property
    def is_gateway(self):
        return self.data.get("gateway")

    @property
    def status(self):
        return self.data.get("status")

    @property
    def serial(self):
        return self.data.get("serial")

    @property
    def update_available(self):
        return self.data.get("update_available")

    @property
    def led_on(self):
        return self.data.get("led_on")

    @led_on.setter
    def led_on(self, value):
        self.api.put(
            url=f"/2.2/eeros/{self.id}/led",
            json=dict(led_on=bool(value)),
        )

    @property
    def connected_clients_count(self):
        return self.data.get("connected_clients_count")


class Profile(Base):

    def __init__(self, api, account, network, data):
        self.api = api
        self.account = account
        self.network = network
        self.data = data

    @property
    def url(self):
        return self.data.get("url")

    @property
    def id(self):
        return self.url.replace(f"/2.2/networks/{self.network.id}/profiles/", "")

    @property
    def name(self):
        return self.data.get("name")

    @property
    def paused(self):
        return self.data.get("paused")

    @paused.setter
    def paused(self, value):
        self.api.put(
            url=f"/2.2/networks/{self.network.id}/profiles/{self.id}",
            json=dict(paused=bool(value)),
        )

    @property
    def block_pornographic_content(self):
        return self.data.get("premium_dns", {}).get("dns_policies", {}).get("block_pornographic_content")

    @block_pornographic_content.setter
    def block_pornographic_content(self, value):
        return self.api.post(
                url=f"/2.2/networks/{self.network.id}/dns_policies/profiles/{self.id}",
                json=dict(block_pornographic_content=bool(value)),
        )

    @property
    def block_illegal_content(self):
        return self.data.get("premium_dns", {}).get("dns_policies", {}).get("block_illegal_content")

    @block_illegal_content.setter
    def block_illegal_content(self, value):
        return self.api.post(
                url=f"/2.2/networks/{self.network.id}/dns_policies/profiles/{self.id}",
                json=dict(block_illegal_content=bool(value)),
        )

    @property
    def block_violent_content(self):
        return self.data.get("premium_dns", {}).get("dns_policies", {}).get("block_violent_content")

    @block_violent_content.setter
    def block_violent_content(self, value):
        return self.api.post(
                url=f"/2.2/networks/{self.network.id}/dns_policies/profiles/{self.id}",
                json=dict(block_violent_content=bool(value)),
        )

    @property
    def safe_search_enabled(self):
        return self.data.get("premium_dns", {}).get("dns_policies", {}).get("safe_search_enabled")

    @safe_search_enabled.setter
    def safe_search_enabled(self, value):
        return self.api.post(
                url=f"/2.2/networks/{self.network.id}/dns_policies/profiles/{self.id}",
                json=dict(safe_search_enabled=bool(value)),
        )


class Client(Base):

    def __init__(self, api, account, network, data):
        self.api = api
        self.account = account
        self.network = network
        self.data = data

    @property
    def url(self):
        return self.data.get("url")

    @property
    def id(self):
        return self.url.replace(f"/2.2/networks/{self.network.id}/devices/", "")

    @property
    def name(self):
        if self.nickname:
            return self.nickname
        elif self.hostname:
            return self.hostname
        return self.mac

    @property
    def name_mac(self):
        return f"{self.name} ({self.mac})"

    @property
    def name_connection_type(self):
        return f"{self.name} ({self.connection_type.title()})"

    @property
    def nickname(self):
        return self.data.get("nickname")

    @property
    def manufacturer(self):
        return self.data.get("manufacturer")

    @property
    def mac(self):
        return self.data.get("mac")

    @property
    def ip(self):
        return self.data.get("ip")

    @property
    def hostname(self):
        return self.data.get("hostname")

    @property
    def connected(self):
        return self.data.get("connected")

    @property
    def wireless(self):
        return self.data.get("wireless")

    @property
    def is_private(self):
        return self.data.get("is_private")

    @property
    def device_type(self):
        return self.data.get("device_type")

    @property
    def connection_type(self):
        return self.data.get("connection_type")

    @property
    def source_location(self):
        return self.data.get("source", {}).get("location")

    @property
    def paused(self):
        return self.data.get("paused")

    @paused.setter
    def paused(self, value):
        return self.api.put(
                url=f"/2.2/networks/{self.network.id}/devices/{self.id}",
                json=dict(paused=bool(value)),
        )

"""Constants used by the system monitor integration."""
import socket
import sys

from homeassistant.const import (
    DATA_GIBIBYTES,
    DATA_MEBIBYTES,
    DATA_RATE_MEGABYTES_PER_SECOND,
    PERCENTAGE,
    TEMP_CELSIUS,
)

CONF_ARG = "arg"

IO_COUNTER = {
    "network_out": 0,
    "network_in": 1,
    "packets_out": 2,
    "packets_in": 3,
    "throughput_network_out": 0,
    "throughput_network_in": 1,
}

IF_ADDRS_FAMILY = {"ipv4_address": socket.AF_INET, "ipv6_address": socket.AF_INET6}

# There might be additional keys to be added for different
# platforms / hardware combinations.
# Taken from last version of "glances" integration before they moved to
# a generic temperature sensor logic.
# https://github.com/home-assistant/core/blob/5e15675593ba94a2c11f9f929cdad317e27ce190/homeassistant/components/glances/sensor.py#L199
CPU_SENSOR_PREFIXES = [
    "amdgpu 1",
    "aml_thermal",
    "Core 0",
    "Core 1",
    "CPU Temperature",
    "CPU",
    "cpu-thermal 1",
    "cpu_thermal 1",
    "exynos-therm 1",
    "Package id 0",
    "Physical id 0",
    "radeon 1",
    "soc-thermal 1",
    "soc_thermal 1",
]

DOMAIN = "systemmonitor"

if sys.maxsize > 2 ** 32:
    CPU_ICON = "mdi:cpu-64-bit"
else:
    CPU_ICON = "mdi:cpu-32-bit"

# Schema: [name, unit of measurement, icon, device class, flag if mandatory arg]
SENSOR_TYPES = {
    "disk_free": ["Disk free", DATA_GIBIBYTES, "mdi:harddisk", None, False],
    "disk_use": ["Disk use", DATA_GIBIBYTES, "mdi:harddisk", None, False],
    "disk_use_percent": [
        "Disk use (percent)",
        PERCENTAGE,
        "mdi:harddisk",
        None,
        False,
    ],
    "ipv4_address": ["IPv4 address", "", "mdi:server-network", None, True],
    "ipv6_address": ["IPv6 address", "", "mdi:server-network", None, True],
    "last_boot": ["Last boot", "", "mdi:clock", "timestamp", False],
    "load_15m": ["Load (15m)", " ", CPU_ICON, None, False],
    "load_1m": ["Load (1m)", " ", CPU_ICON, None, False],
    "load_5m": ["Load (5m)", " ", CPU_ICON, None, False],
    "memory_free": ["Memory free", DATA_MEBIBYTES, "mdi:memory", None, False],
    "memory_use": ["Memory use", DATA_MEBIBYTES, "mdi:memory", None, False],
    "memory_use_percent": [
        "Memory use (percent)",
        PERCENTAGE,
        "mdi:memory",
        None,
        False,
    ],
    "network_in": ["Network in", DATA_MEBIBYTES, "mdi:server-network", None, True],
    "network_out": ["Network out", DATA_MEBIBYTES, "mdi:server-network", None, True],
    "packets_in": ["Packets in", " ", "mdi:server-network", None, True],
    "packets_out": ["Packets out", " ", "mdi:server-network", None, True],
    "throughput_network_in": [
        "Network throughput in",
        DATA_RATE_MEGABYTES_PER_SECOND,
        "mdi:server-network",
        None,
        True,
    ],
    "throughput_network_out": [
        "Network throughput out",
        DATA_RATE_MEGABYTES_PER_SECOND,
        "mdi:server-network",
        True,
    ],
    "process": ["Process", " ", CPU_ICON, None, True],
    "processor_use": ["Processor use (percent)", PERCENTAGE, CPU_ICON, None, False],
    "processor_temperature": [
        "Processor temperature",
        TEMP_CELSIUS,
        CPU_ICON,
        None,
        False,
    ],
    "swap_free": ["Swap free", DATA_MEBIBYTES, "mdi:harddisk", None, False],
    "swap_use": ["Swap use", DATA_MEBIBYTES, "mdi:harddisk", None, False],
    "swap_use_percent": ["Swap use (percent)", PERCENTAGE, "mdi:harddisk", None, False],
}

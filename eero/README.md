## Eero Integration for Home Assistant

Adds support for [Eero Wi-Fi routers](https://eero.com/) to [Home Assistant](https://www.home-assistant.io/).

This project is originally based on [@343max's eero-client project](https://github.com/343max/eero-client) and [@jrlucier's eero_tracker project](https://github.com/jrlucier/eero_tracker) work. Many thanks to their efforts.

## Features

- Full config flow implementation, no need for scripts or YAML
- Sensors for available updates, public IP, speed test results, connected client count, and more
- Device trackers for wired and wireless clients
- Switches for guest network, LED status light, and connection pausing; additional switches for Eero Secure features (i.e. ad blocking, advanced security, etc.) if subscription exists

## Setup Process

1. Manually copy the files to custom_components directory
2. Restart Home Assistant
3. Go to Integrations and search for "eero"
4. Follow the prompts
5. Once setup is finished, use the integration options to configure polling interval and desired Eero devices/profiles/clients

#### Remaining Work

These features are in process of being implemented.

- Service to reboot the entire Eero network
- Sensors for activity data (i.e. data usage, ad blocks, scans, etc.)
- Switches for Eero labs features (i.e. band steering, local DNS caching, etc.)
- Eero beacon nightlight control

#### Home Assistant Native Integration

The following will need to be addressed before a PR against Home Assistant should be created. I don't plan on attacking this right away as my time is limited, any help would be appreciated.

- Publish client as a separate PyPi package
- Various code cleanup (i.e. strings, translations, docstrings, ID vs URL reference for resources, etc.)
- Performance improvement (especially if activity data support is added as many additional calls will be required)
- Add tests
- Remove option for saving responses (currently there for development help)

## See Also

* [Eero Device Tracker for Home Assistant](https://github.com/jrlucier/eero_tracker)
* [Eero Python Client (343max/eero-client)](https://github.com/343max/eero-client)

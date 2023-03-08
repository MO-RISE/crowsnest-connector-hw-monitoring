# Crowsnest HW monitoring

A crowsnest setup for monitoring and logging hardware usage on Ubuntu. Two services are used to monitor the HW state.

1. Netdata a monitoring dashboard on local network
2. Python script pushing HW state to local MQTT broker

## [Netdata](https://www.netdata.cloud/open-source/)

Netdata is a lightweight, open-source, and community-driven open-source monitoring and logging solution. It is designed to be easy to install, configure,

- Netdata dashboard: http://localhost:19999
- Configuration file: http://localhost:19999/netdata.conf

SSH Local Forwarding can be used to access the dashboard remotely.

## HW info to MQTT broker

Python script reading hardware state and pushes it to selected MQTT broker.

Recommended setup is pushing the HW state to local MQTT broker and then using [Crowsnest bridge](https://github.com/MO-RISE/crowsnest-bridge-mqtt) to make the data remotely available.

Pushing following HW state to local MQTT broker:

- [x] Boot time
- [x] CPU temperature and usage
- [x] GPU temperature and usage
- [x] RAM/Memory
- [x] Disk space
TODO:
- [ ] Power 

## Example setup

Copy file [docker-compose.hw-logger.yml](docker-compose.hw-logger.yml) to an folder and change 

`build: .` 

to 

`image:image: ghcr.io/mo-rise/crowsnest-processor-hw-logger:latest` 



Variables:
```bash
# Run command
docker-compose -f docker-compose.hw-logger.yml up -d 

```

## Development

Requires:

- python >= 3.8
- docker and docker-compose

Install the python requirements in a virtual environment:

```cmd
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements_dev.txt
```

from environs import Env
import os
import time
import sched
from datetime import datetime, timezone
import logging
import threading
import warnings
from paho.mqtt.client import Client as MQTT
from streamz import Stream
from brefv_spec.envelope import Envelope
import platform
import psutil
import pytz
import GPUtil
from hw import get_readable_size

# Reading config from environment variables
env = Env()
# MQTT
MQTT_BROKER_HOST: str = env("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT: int = env.int("MQTT_BROKER_PORT", 1883)
MQTT_CLIENT_ID: str = env("MQTT_CLIENT_ID", None)
MQTT_TRANSPORT: str = env("MQTT_TRANSPORT", "tcp")
MQTT_TLS: bool = env.bool("MQTT_TLS", False)
MQTT_USER: str = env("MQTT_USER", None)
MQTT_PASSWORD: str = env("MQTT_PASSWORD", None)
MQTT_TOPIC_JSON_OUT: str = env("MQTT_TOPIC_JSON_OUT", "CROWSNEST/DEV/HW/0/JSON")
MQTT_TOPIC_JSON_OUT: str = env("MQTT_TOPIC_JSON_OUT", "CROWSNEST/DEV/HW/0/JSON")

# Setup logger
LOG_LEVEL = env.log_level("LOG_LEVEL", "WARNING")  # WARNING, DEBUG,INFO
logging.basicConfig( format="%(asctime)s %(levelname)s %(name)s %(message)s",level=LOG_LEVEL)
logging.captureWarnings(True)
warnings.filterwarnings("once")
LOGGER = logging.getLogger("hw-logger")

# Create mqtt client and configure it according to configuration
mq = MQTT(client_id=MQTT_CLIENT_ID, transport=MQTT_TRANSPORT)
mq.username_pw_set(MQTT_USER, MQTT_PASSWORD)
if MQTT_TLS:
    mq.tls_set()
mq.enable_logger(LOGGER)


def to_brefv_raw(in_msg: dict):
    """
    Raw in message to brefv envelope

    Inout:
        in_msg: dictionary

    Returns:
        Brefv Envelope

    """

    envelope = Envelope(
        sent_at=datetime.now(timezone.utc).isoformat(),
        message=in_msg,
    )
    LOGGER.debug("Assembled into brefv envelope: %s", envelope)
    return envelope.json()


def to_mqtt(payload: any, topic: str):
    """Publish a payload to a mqtt topic"""

    LOGGER.debug("Publishing on %s with payload: %s", topic, payload)
    try:
        mq.publish(
            topic,
            payload,
        )
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Failed publishing to broker!")

    return "NEXT"


#######################################################################
# HW info


def collect_hw_info(aa):
    """Collect hardware info"""

    LOGGER.info("Collecting hardware info")
    uname = platform.uname()

    # Boot time
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    bt = bt.replace(tzinfo=pytz.timezone("Europe/Stockholm"))
    bt_str = bt.isoformat()
    # bt_str = f"{bt.year}-{bt.month}-{bt.day} {bt.hour}:{bt.minute}:{bt.second}"

    # CPU info
    cpu_mean_temp = None
    if uname.system == "Linux":
        try:
            cpu_core_temps = []
            # sensors_temperatures not available on Windows (2023-03-06)
            for i in range(len(psutil.sensors_temperatures()["coretemp"])):
                cpu_core_temps.append(psutil.sensors_temperatures()["coretemp"][i].current)
            cpu_mean_temp = sum(cpu_core_temps) / len(cpu_core_temps)
            # print("CPU temp mean:", (sum(cpu_core_temps) / len(cpu_core_temps)), "°C")
        except Exception as  e:
            LOGGER.warning("Failed to collect CPU temperature")
            LOGGER.warning(f"Exception: {e}")

    # RAM 
    svmem = psutil.virtual_memory()
    
    # GPUS
    gpus = GPUtil.getGPUs()
    gpus_info = []
    if len(gpus) < 1:
        LOGGER.warning("No GPU found")
    else:
        for gpu in gpus:
            gpus_info.append(
                {
                    "name": gpu.name,
                    "load_procreant": gpu.load * 100,
                    "temperature": gpu.temperature,
                    "memory_free_MB": gpu.memoryFree,
                    "memory_used_MB": gpu.memoryUsed,
                    "memory_total_MB": gpu.memoryTotal,
                }
            )

    # Get all disk partitions
    partitions = psutil.disk_partitions()
    partition_list = []
    for partition in partitions[:]:
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            # this can be catched due to the disk that
            # isn't ready
            continue
        partition_list.append({
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "total_size": get_readable_size(partition_usage.total),
            "used_size": get_readable_size(partition_usage.used),
            "free_size": get_readable_size(partition_usage.free),
            "percent_used": partition_usage.percent,
        })

    return {
        "op_system": uname.system,
        "sys_name": uname.node,
        "boot_time": bt_str,
        "cpu_load_procreant": psutil.cpu_percent(),
        "cpu_temp": cpu_mean_temp,
        "ram_usage": svmem.percent,
        "ram_size": get_readable_size(svmem.total),
        "gpus": gpus_info,
        "partition": partition_list
    }


def trigger_collector():
    source.emit("sd")


if __name__ == "__main__":
    # Connecting to MQTT
    LOGGER.info("Connecting to MQTT broker...")
    mq.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)

    # Build pipeline
    LOGGER.info("Building pipeline...")
    global source
    source = Stream()

    # MQTT Streamz Loop
    # 'rate_limit' in seconds determines the output rate
    pipe_hw_info_to_brefv = (
        source.rate_limit(5).map(collect_hw_info).map(to_brefv_raw).map(to_mqtt, topic=MQTT_TOPIC_JSON_OUT)
    )
    pipe_hw_info_to_brefv.connect(source)

    source.emit("start")

    # Socket Multicast runs in the foreground so we put the MQTT stuff in a separate thread
    # threading.Thread(target=mq.loop_forever, daemon=True).start()

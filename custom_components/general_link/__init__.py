import logging
import time
import asyncio
import json

from homeassistant.const import __version__
from homeassistant.components import network
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_ADDRESS
from homeassistant.helpers import config_validation as cv, entity_platform, service
from ipaddress import ip_network
from .listener import sender_receiver
from .Gateway import Gateway
from .const import PLATFORMS, MQTT_CLIENT_INSTANCE, CONF_LIGHT_DEVICE_TYPE, DOMAIN, FLAG_IS_INITIALIZED, \
    CACHE_ENTITY_STATE_UPDATE_KEY_DICT, CONF_BROKER, CONF_ENVKEY, CONF_PLACE,MQTT_TOPIC_PREFIX,TEMP_MQTT_TOPIC_PREFIX
from .mdns import MdnsScanner
from .http_get import HttpRequest

_LOGGER = logging.getLogger(__name__)
reconnect_flag = asyncio.Event()

#temp_ll = None

async def _async_config_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """当配置项更新时的异步处理函数。
    参数:
    - hass: HomeAssistant对象，表示Home Assistant实例。
    - entry: ConfigEntry对象，表示配置项。
    """
    _LOGGER.debug(f"_async_config_entry_updated {entry.data}")
    hub = hass.data[DOMAIN][entry.entry_id]
    hass.async_create_task(
        hub.init(entry, False)
    )




async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """基于配置项的异步设置函数。
    参数:
    - hass: HomeAssistant对象，表示Home Assistant实例。
    - entry: ConfigEntry对象，表示配置项。
    返回:
    - bool: 表示设置是否成功。
    """
    """Set up from a config entry."""

    hub = Gateway(hass, entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub

    # 初始化标记和实体状态更新键字典
    hass.data.setdefault(FLAG_IS_INITIALIZED, False)
    hass.data.setdefault(CACHE_ENTITY_STATE_UPDATE_KEY_DICT, {})
    hass.data.setdefault(TEMP_MQTT_TOPIC_PREFIX, {})

    # 如果尚未初始化，则进行初始化操作
    if not hass.data[FLAG_IS_INITIALIZED]:
        hass.data[FLAG_IS_INITIALIZED] = True
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 启用重连标志
    hub.reconnect_flag = True

    hass.async_create_task(
        hub.init(entry, True)
    )

    reconnect_flag.clear()
    
    _LOGGER.debug(f"entry.data ,{entry.data}")
    # hub.init_state = True

    # reconnect_flag = asyncio.Event()

    # 注册配置项更新监听器

    entry.async_on_unload(entry.add_update_listener(
        _async_config_entry_updated))
    

    """
    adapters = await network.async_get_adapters(hass)

    for adapter in adapters:
        if adapter["enabled"] and adapter["name"] == "eth0":

            for ip_info in adapter["ipv4"]:
                local_ip = ip_info["address"]
                network_prefix = ip_info["network_prefix"]
                ip_net = ip_network(f"{local_ip}/{network_prefix}", False)
                _LOGGER.warning(f"local_ip ,{local_ip} ip_net, {ip_net}")
    _LOGGER.warning(f"adapters ,{adapters}")
    """


    _LOGGER.warning(f"homeassistant.version ,{__version__}")
    

    async def custom_push_mqtt(call):

        topic = call.data.get("topic", "P/0/center/q24")
        data = call.data.get("data")
        global temp_ll
        subscribe_topic = f"{MQTT_TOPIC_PREFIX}/{entry.data['mqttAddr']}/{'/'.join(topic.split('/')[-2:]).replace('q', 'p')}"
        
        
        if subscribe_topic not in hass.data[TEMP_MQTT_TOPIC_PREFIX]:
           await hub.mqtt_subscribe_custom(subscribe_topic)
           hass.data[TEMP_MQTT_TOPIC_PREFIX][subscribe_topic] = True
        _LOGGER.warning(f"topic,{hass.data[TEMP_MQTT_TOPIC_PREFIX]}")
        # if topic == "P/0/center/q24":
        #  data = call.data
        # else:

        await hub.async_mqtt_publish(topic, data)



        # hass.states.set(f"{DOMAIN}.PUSH", payload)

        return True

    hass.services.async_register(DOMAIN, "custom_push_mqtt", custom_push_mqtt)
    

    async def get_backupconfig(call):
        name = call.data.get("name")
        password = call.data.get("password")
        url = call.data.get("url","api.iot.9451.com.cn")
        manufacturer = call.data.get("manufacturer", "Netmoon")
        envKey = call.data.get("envKey","123456")
        hr= HttpRequest(hass, name, password, url, manufacturer)
        response = await hr.get_envkey()

        message = json.dumps(response,ensure_ascii=False,indent=4)
        
        await hass.services.async_call(

        "persistent_notification", "create", {"title":"场所信息","message": message,"notification_id": 1}, blocking=True

        )
        responsebackup = await hr.get_backupfile(envKey)

        message = json.dumps(responsebackup,ensure_ascii=False,indent=4)
        await hass.services.async_call(

        "persistent_notification", "create", {"title":"备份信息","message": message,"notification_id": 2}, blocking=True

        )
        return True
    
    hass.services.async_register(DOMAIN, "get_backupconfig", get_backupconfig)
    

    hass.async_create_background_task(

        monitor_connection(hass, hub, entry, reconnect_flag),

        "monitor_connection"

    )

    return True


async def monitor_connection(hass, hub, entry, reconnect_flag):
    """监控连接的异步函数。
    参数:
    - hass: HomeAssistant对象，表示Home Assistant实例。
    - hub: Gateway对象，表示网关。
    - entry: ConfigEntry对象，表示配置项。
    - reconnect_flag: asyncio.Event对象，用于控制重连逻辑。
    """
    scanner = MdnsScanner(hass)

    last_sync_time = 0  # 用于记录上一次同步的时间

    while not reconnect_flag.is_set():

        await asyncio.sleep(10)  # 每20秒检测一次连接状态

        try:

            # 检查MQTT连接状态

            mqtt_connected = hub.hass.data[MQTT_CLIENT_INSTANCE].connected
            current_time = int(time.time())
            

            # 如果MQTT未连接或网关初始化状态为False，则尝试重新连接
            if not mqtt_connected or not hub.init_state:
                hub.reconnect_flag = True

                connection = None

                # await zeroconf.async_setup(hass,entry)
                # 通过mDNS扫描设备
                if CONF_PLACE in entry.data:
                    try:
                        connection = await sender_receiver(hass, entry.data[CONF_ENVKEY], entry.data[CONF_PASSWORD], entry.data[CONF_PLACE], dest_address=entry.data[CONF_ADDRESS])
                    except Exception as e:
                        _LOGGER.error("sender_receiver %s", e)
                else:
                    connection = await scanner.scan_single(entry.data[CONF_NAME], 2)

                _LOGGER.debug("mqtt 连接不上了，需要重新扫描一下，得到连接 %s", connection)
                _LOGGER.warning("mqtt 连接不上了，重新扫描一下")

                

                # 如果扫描到设备，更新配置项数据
                if connection is not None:

                    if CONF_LIGHT_DEVICE_TYPE in entry.data:

                        connection[CONF_LIGHT_DEVICE_TYPE] = entry.data[CONF_LIGHT_DEVICE_TYPE]

                        connection["random"] = time.time()

                    try:

                        hass.config_entries.async_update_entry(
                            entry, data=connection)

                    except Exception as e:

                        _LOGGER.error("Error in update_entry: %s", e)
                # 如果没扫描到设备，但是MQTT已连接，则尝试重新初始化网关
                elif connection is None and mqtt_connected and not hub.init_state:
                    _LOGGER.warning("没扫描到设备，但是MQTT已连接")
                    await _async_config_entry_updated(hass, entry)

            # 每300秒同步一次群组状态
            elif current_time - last_sync_time >= 300:
                _LOGGER.debug(f"current_time{current_time}last_sync_time{last_sync_time}")
                last_sync_time = current_time

                await hub.sync_group_status(False)

        except Exception as e:

            _LOGGER.error("Error in monitor_connection: %s", e)

        await asyncio.sleep(10)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置项的异步函数。
    参数:
    - hass: HomeAssistant对象，表示Home Assistant实例。
    - entry: ConfigEntry对象，表示配置项。
    返回:
    - bool: 表示卸载是否成功。
    """
    reconnect_flag.set()  # Notify monitor_connection to stop

    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    hub = hass.data[DOMAIN].pop(entry.entry_id)

    await hub.disconnect()

    hass.data[CACHE_ENTITY_STATE_UPDATE_KEY_DICT] = {}

    return True

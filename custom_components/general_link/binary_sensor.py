import logging
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, EVENT_ENTITY_REGISTER, EVENT_ENTITY_STATE_UPDATE, CACHE_ENTITY_STATE_UPDATE_KEY_DICT, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

COMPONENT = "binary_sensor"
INPUT_SCHEMA = ['a100','a101','a102','a103']

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """根据配置入口设置二进制传感器实体"""

    async def async_discover(config_payload):
        try:
            if "a15" in config_payload:
                async_add_entities([MotionA15Sensor(hass, config_payload, config_entry)])
            elif "a100" in config_payload:
                unique_id = config_payload['unique_id']
                name = config_payload['name']
               
                for i, inputname in enumerate(INPUT_SCHEMA,start=1):
                   config_payload['unique_id'] = f"{unique_id}_{inputname}"
                   config_payload['name'] = f"{name}_{i}"
                   config_payload['inputname'] = inputname
                   
                   async_add_entities([MotionA100Sensor(hass, config_payload, config_entry)])

        except Exception :
            raise

    unsub = async_dispatcher_connect(
        hass, EVENT_ENTITY_REGISTER.format(COMPONENT), async_discover
    )

    config_entry.async_on_unload(unsub)


class MotionSensor(BinarySensorEntity):
    """用于处理占用传感器相关的业务逻辑的自定义实体类"""

    should_poll = False
    
    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        
        #self._attr_name = config["name"] + "_存在"
        #self._device_class = BinarySensorDeviceClass.MOTION
        #self._attr_is_on = bool(config["a15"])
        self.dname = config["name"]
        self.sn = config["sn"]
        self._model = config["model"]
        self._attr_available = True
        self.hass = hass
        self.config_entry = config_entry
        self.update_state(config)

        key = EVENT_ENTITY_STATE_UPDATE.format(self.unique_id)
        if key not in hass.data[CACHE_ENTITY_STATE_UPDATE_KEY_DICT]:
            unsub = async_dispatcher_connect(
                hass, key, self.async_discover
            )
            hass.data[CACHE_ENTITY_STATE_UPDATE_KEY_DICT][key] = unsub
            config_entry.async_on_unload(unsub)

    @callback
    def async_discover(self, data: dict) -> None:
        try:
            self.update_state(data)
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"更新传感器状态时出错: {e}")
    def update_state(self, data) -> None:
        if "state" in data:
            if data["state"] == 1:
                self._attr_available = True
            elif data["state"] == 0:
                self._attr_available = False
    @property
    def device_info(self) -> DeviceInfo:
        """关于此实体/设备的信息"""
        return {
            "identifiers": {(DOMAIN, self.sn)},
            "serial_number": self.sn,
            "model": self._model,
            "name": self.dname,
            "manufacturer": MANUFACTURER,
        }


class MotionA15Sensor(MotionSensor):
    """用于处理占用传感器相关的业务逻辑的自定义实体类"""
    device_class = BinarySensorDeviceClass.MOTION

    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        self._attr_unique_id = config["unique_id"] + "M"
        self._attr_name = config["name"] + "_存在"
        self._attr_is_on = bool(config["a15"])
        super().__init__(hass, config, config_entry)


    def update_state(self, data: dict):
        """传感器事件报告更改HA中的传感器状态"""
        super().update_state(data)
        if "a15" in data:
            self._attr_is_on = bool(data["a15"])

class MotionA100Sensor(MotionSensor):
    """用于处理占用传感器相关的业务逻辑的自定义实体类"""
    device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        self._attr_unique_id = config["unique_id"]
        self._attr_name = config["name"] 
        self._input = config["inputname"]
        self._attr_is_on = bool(config[self._input])
        super().__init__(hass, config, config_entry)
        

    def update_state(self, data: dict):
        """传感器事件报告更改HA中的传感器状态"""
        super().update_state(data)
        if self._input in data:
            self._attr_is_on = bool(data[self._input])


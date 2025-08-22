"""业务逻辑用于表示光照水平传感器的传感器实体"""

import logging
from homeassistant.components.sensor import SensorEntity,SensorDeviceClass,SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import LIGHT_LUX,UnitOfElectricPotential,UnitOfElectricCurrent,UnitOfEnergy,UnitOfPower

from .const import DOMAIN, EVENT_ENTITY_REGISTER, EVENT_ENTITY_STATE_UPDATE, CACHE_ENTITY_STATE_UPDATE_KEY_DICT, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

COMPONENT = "sensor"

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """根据配置入口设置传感器实体"""

    async def async_discover(config_payload):
        try:
            if "a14" in config_payload:
                async_add_entities([LightSensor(hass, config_payload, config_entry)])
            if "a155" in config_payload:
                async_add_entities([VoltageSensor(hass, config_payload, config_entry)])
            if "a158" in config_payload:
                async_add_entities([CurrentSensor(hass, config_payload, config_entry)])
            if "a173" in config_payload:
                async_add_entities([EnergySensor(hass, config_payload, config_entry)])
            if "a161" in config_payload:
                async_add_entities([PowerA161Sensor(hass, config_payload, config_entry)])
            

        except Exception :
            raise

    unsub = async_dispatcher_connect(
        hass, EVENT_ENTITY_REGISTER.format(COMPONENT), async_discover
    )

    config_entry.async_on_unload(unsub)


class LightSensor(SensorEntity):
    """用于处理光照传感器相关的业务逻辑的自定义实体类"""

    should_poll = False
    0

    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        self._attr_unique_id = config["unique_id"]+"L"
        self._attr_name = config["name"]+"_光照"
        #self._attr_entity_id = config["unique_id"]+"L"
        self.dname = config["name"]
        self._model = config["model"]
        self._device_class = SensorDeviceClass.ILLUMINANCE
        self._attr_native_unit_of_measurement = LIGHT_LUX
        self._attr_native_value = config["a14"]
        self._attr_available = True
        self.sn = config["sn"]
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

    @property
    def device_info(self) -> DeviceInfo:
        """关于此实体/设备的信息"""
        return {
            "identifiers": {(DOMAIN, self.sn)},
            "model": self._model,
            "serial_number": self.sn,
            "name": self.dname,
            "manufacturer": MANUFACTURER,
        }

    def update_state(self, data):
        """传感器事件报告更改HA中的传感器状态"""
        if "a14" in data:
            self._attr_native_value = data["a14"]
        if "state" in data:
            if data["state"] == 1:
                self._attr_available = True
            elif data["state"] == 0:
                self._attr_available = False

class VoltageSensor(SensorEntity):
    """用于处理光照传感器相关的业务逻辑的自定义实体类"""

    should_poll = False
    

    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        self._attr_unique_id = config["unique_id"]+"V"
        self._attr_name = config["name"]+"_电压"
        #self._attr_entity_id = config["unique_id"]+"L"
        self.dname = config["name"]
        self._model = config["model"]
        self._device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_native_value = config["a155"]
        self.sn = config["sn"]
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

    @property
    def device_info(self) -> DeviceInfo:
        """关于此实体/设备的信息"""
        return {
            "identifiers": {(DOMAIN, self.sn)},
            "model": self._model,
            "serial_number": self.sn,
            "name": self.dname,
            "manufacturer": MANUFACTURER,
        }

    def update_state(self, data):
        """传感器事件报告更改HA中的传感器状态"""
        if "a155" in data:
            self._attr_native_value = data["a155"]
        
        if "state" in data:
            if data["state"] == 1:
                self._attr_available = True
            elif data["state"] == 0:
                self._attr_available = False


class CurrentSensor(SensorEntity):
    """用于处理光照传感器相关的业务逻辑的自定义实体类"""

    should_poll = False
    

    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        
        self._attr_unique_id = config["unique_id"]+"C"
        self._attr_name = config["name"]+"_电流"
        #self._attr_entity_id = config["unique_id"]+"L"
        self.dname = config["name"]
        self._model = config["model"]
        self._device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_native_value = config["a158"]
        self.sn = config["sn"]
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

    @property
    def device_info(self) -> DeviceInfo:
        """关于此实体/设备的信息"""
        return {
            "identifiers": {(DOMAIN, self.sn)},
            "model": self._model,
            "serial_number": self.sn,
            "name": self.dname,
            "manufacturer": MANUFACTURER,
        }

    def update_state(self, data):
        """传感器事件报告更改HA中的传感器状态"""
        if "a158" in data:
            self._attr_native_value = data["a158"]
        if "state" in data:
            if data["state"] == 1:
                self._attr_available = True
            elif data["state"] == 0:
                self._attr_available = False

class EnergySensor(SensorEntity):
    """用于处理光照传感器相关的业务逻辑的自定义实体类"""

    should_poll = False
    

    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        self._attr_unique_id = config["unique_id"]+"E"
        self._attr_name = config["name"]+"_用电量"
        #self._attr_entity_id = config["unique_id"]+"L"
        self.dname = config["name"]
        self._device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_value = config["a173"]
        self._model = config["model"]
        self.sn = config["sn"]
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

    @property
    def device_info(self) -> DeviceInfo:
        """关于此实体/设备的信息"""
        return {
            "identifiers": {(DOMAIN, self.sn)},
            "model": self._model,
            "serial_number": self.sn,
            "name": self.dname,
            "manufacturer": MANUFACTURER,
        }

    def update_state(self, data):
        """传感器事件报告更改HA中的传感器状态"""
        if "a173" in data:
            self._attr_native_value = data["a173"]
        if "state" in data:
            if data["state"] == 1:
                self._attr_available = True
            elif data["state"] == 0:
               self._attr_available = False

class PowerA161Sensor(SensorEntity):
    """用于处理光照传感器相关的业务逻辑的自定义实体类"""

    should_poll = False
    #device_class = SensorDeviceClass.ILLUMINANCE

    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        self._attr_unique_id = config["unique_id"]+"P"
        self._attr_name = config["name"]+"_有功功率"
        #self._attr_entity_id = config["unique_id"]+"L"
        self.dname = config["name"]
        self._device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        self._attr_native_value = config["a161"]
        self._model = config["model"]
        self.sn = config["sn"]
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

    @property
    def device_info(self) -> DeviceInfo:
        """关于此实体/设备的信息"""
        return {
            "identifiers": {(DOMAIN, self.sn)},
            "model": self._model,
            "serial_number": self.sn,
            "name": self.dname,
            "manufacturer": MANUFACTURER,
        }

    def update_state(self, data):
        """传感器事件报告更改HA中的传感器状态"""
        if "a161" in data:
            self._attr_native_value = data["a161"]
        if "state" in data:
            if data["state"] == 1:
                self._attr_available = True
            elif data["state"] == 0:
               self._attr_available = False
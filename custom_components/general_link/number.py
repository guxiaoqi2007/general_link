"""Business logic for number entity."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode,NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MQTT_CLIENT_INSTANCE, EVENT_ENTITY_REGISTER, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

COMPONENT = "number"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities from config entry."""

    async def async_discover(config_payload):
        try:
            async_add_entities([CustomNumber(hass, config_payload, config_entry)])
        except Exception as e:
            _LOGGER.error("Failed to add number entity: %s", e)
            raise

    unsub = async_dispatcher_connect(
        hass, EVENT_ENTITY_REGISTER.format(COMPONENT), async_discover
    )

    config_entry.async_on_unload(unsub)


class CustomNumber(NumberEntity):
    """Custom number entity that supports negative values and MQTT control."""

    _attr_should_poll = False
    _attr_device_class = NumberMode.BOX  # or NumberMode.SLIDER if preferred

    def __init__(
        self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry
    ) -> None:
        self.hass = hass
        self.config_entry = config_entry
        self.mqttAddr = config_entry.data.get("mqttAddr", 0)
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        # Required attributes
        self._attr_unique_id = config["unique_id"]+"N"
        self._attr_name = config["name"]+"_温度补偿"
        self._dname = config["name"]
        

        # Optional: room-based device grouping
        self._sn = config["sn"]
        
        # Number-specific attributes — 支持负数的关键！
        self._attr_native_min_value = -10
        self._attr_native_max_value = 10
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "°C"

        # Initial value (must be within min/max)
        initial = 0
        self._attr_native_value = float(initial)

    @property
    def device_info(self) -> DeviceInfo:
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._sn)},
            "serial_number": self._sn,
            # If desired, the name for the device could be different to the entity
            "name": self._dname,
            "manufacturer": MANUFACTURER,
        }

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value and send command via MQTT."""
        self._attr_native_value = value
        await self.async_exec_command(value)
        self.async_write_ha_state()

    async def async_exec_command(self, value: float) -> None:
        """Send the number value to device via MQTT."""
        message = {
            "seq": 1,
            "rspTo": "A/hass",
            "s": 
            {
                "t": 101
            },  # 假设 t=201 表示设置数值型参数
            
            "data": {
                "i": 62,
                "sn": self._sn,
                "p":{
                "a19": int(value)
                }
            }
        }

        await self.hass.data[MQTT_CLIENT_INSTANCE].async_publish(
            f"P/{self.mqttAddr}/center/q74",
            json.dumps(message),
            qos=0,
            retain=False,
        )
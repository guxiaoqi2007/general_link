from homeassistant.helpers.entity import Entity
import logging
from homeassistant.core import callback
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import (
    DOMAIN,
)
_LOGGER = logging.getLogger(__name__)
# 假设您的集成名为 'my_integration'


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """设置事件实体"""
    _LOGGER.warning("设置事件实体")
    async_add_entities([MyCustomEventEntity(hass)])
    

class MyCustomEventEntity(EventEntity):
    """自定义事件实体"""

    def __init__(self, hass: HomeAssistant):
        """初始化事件实体"""
        super().__init__()
        self._attr_name = "report_q8"
        self._attr_unique_id = f"{DOMAIN}_report_q8_event"
        self.hass = hass
        # 订阅感兴趣的事件类型
        self.event_types = ["report_q8"]  # 这里替换为您想监听的事件类型
        self.unsub = None

    async def async_added_to_hass(self) -> None:
        """当实体被添加到Hass时调用"""
        await super().async_added_to_hass()
        # 注册事件监听器
        for event_type in self.event_types:
            self.unsub = self.hass.bus.async_listen(event_type, self.handle_event)
        

    async def async_will_remove_from_hass(self) -> None:
        """当实体将从Hass中移除时调用"""
        if self.unsub is not None:
            self.unsub()

    @callback
    def handle_event(self, event: Event):
        """处理接收到的事件"""
        _LOGGER.warning(f"接收到了事件 {event.event_type}，数据：{event.data}")
        # 在这里可以根据事件的内容执行相应的操作
        # 例如：更新状态、发送通知等
        self._attr_state = STATE_ON  # 更新实体状态
        self.async_write_ha_state()  # 通知前端更新状态
        
        # 示例：如果需要基于事件内容做更多处理
        if event.data.get('important_key') == 'expected_value':
            self.perform_additional_actions()

    def perform_additional_actions(self):
        """在此方法中实现额外的动作"""
        _LOGGER.warning("执行额外的操作...")
"""Define a gateway class for managing MQTT connections within the gateway"""

import asyncio
import json
import logging
import time
from datetime import datetime
import pytz
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.components.mqtt.const import CONF_CERTIFICATE
from .mdns import MdnsScanner
from .const import MQTT_CLIENT_INSTANCE, CONF_LIGHT_DEVICE_TYPE, EVENT_ENTITY_REGISTER, MQTT_TOPIC_PREFIX, \
    EVENT_ENTITY_STATE_UPDATE, DEVICE_COUNT_MAX,TEMP_MQTT_TOPIC_PREFIX
from .mqtt import MqttClient

from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)
INPUT_SCHEMA = ['a100','a101','a102','a103']
SOURCE_TYPE = {
    1: "云端",
    2: "移动端APP",
    3: "场所管理中心（主网关）",
    4: "子设备",
    100: "HomeKit",
    101: "HomeAssistant",
    102: "天猫精灵",
    103: "小度音响"
}
#目的类型
DESTINATION_TYPE = {
    1: "云端",
    2: "移动端APP",
    3: "场所管理中心（主网关）",
    4: "子设备",
    5: "多设备",
    6: "组设备"
}
NMNLOG_TEMPLATES = {
    0x00000001: "设备第{0}次启动。",
    0x00000003: "设备启动{0}秒时，同步到UTC时间。",
    0x00000500: "自动化执行之计划任务，编号：{0}；场景：{1}",
    0x00000501: "自动化执行之设备触发，编号：{0}；场景：{1}；设备：{2}；属性：{3}；值：{4}",
    0x00000600: "执行场景，编号：{0}",
    0x00010100: "关闭单灯{0}",
    0x00010101: "打开单灯{0}",
    0x00010102: "将单灯{0}亮度调整到：{1}%",
    0x00010103: "调亮单灯{0}",
    0x00010104: "调暗单灯{0}",
    0x00010105: "单步调整单灯{0}亮度，步进：{1}%",
    0x00010106: "将单灯{0}色温调整到：{1}K",
    0x00010107: "将单灯{0}色温调高一些",
    0x00010108: "将单灯{0}色温调低一些",
    0x00010109: "单步调整单灯{0}色温，步进：{1}K",
    0x0001010A: "将单灯{0}RGB色彩值调整到：#{1}",
    # 多灯命令
    0x00010150: "关闭多灯{0}",
    0x00010151: "打开多灯{0}",
    0x00010152: "将多灯{0}亮度调整到：{1}%",
    0x00010153: "调亮多灯{0}",
    0x00010154: "调暗多灯{0}",
    0x00010155: "单步调整多灯{0}亮度，步进：{1}%",
    0x00010156: "将多灯{0}色温调整到：{1}K",
    0x00010157: "将多灯{0}色温调高一些",
    0x00010158: "将多灯{0}色温调低一些",
    0x00010159: "单步调整多灯{0}色温，步进：{1}K",
    0x0001015A: "将多灯{0}RGB色彩值调整到：#{1}",
    # 灯组命令
    0x000101A0: "关闭灯组【房间：{0}，子组：{1}】",
    0x000101A1: "打开灯组【房间：{0}，子组：{1}】",
    0x000101A2: "将灯组【房间：{0}，子组：{1}】亮度调整到：{2}%",
    0x000101A3: "调亮灯组【房间：{0}，子组：{1}】",
    0x000101A4: "调暗灯组【房间：{0}，子组：{1}】",
    0x000101A5: "单步调整灯组【房间：{0}，子组：{1}】亮度，步进：{2}%",
    0x000101A6: "将灯组【房间：{0}，子组：{1}】色温调整到：{2}K",
    0x000101A7: "将灯组【房间：{0}，子组：{1}】色温调高一些",
    0x000101A8: "将灯组【房间：{0}，子组：{1}】色温调低一些",
    0x000101A9: "单步调整灯组【房间：{0}，子组：{1}】色温，步进：{2}K",
    0x000101AA: "将灯组【房间：{0}，子组：{1}】RGB色彩值调整到：#{2}",
    # 开关继电器命令
    0x00010200: "关闭开关{0}的第{1}个继电器",
    0x00010201: "打开开关{0}的第{1}个继电器",
    # 单窗帘命令
    0x00010300: "停止单窗帘{0}",
    0x00010301: "打开单窗帘{0}",
    0x00010302: "关闭单窗帘{0}",
    0x00010303: "将单窗帘{0}行程调整到：{1}%",
    0x00010308: "向左旋转单窗帘{0}叶片",
    0x00010309: "向右旋转单窗帘{0}叶片",
    0x0001030A: "停止旋转单窗帘{0}叶片",
    0x0001030B: "将单窗帘{0}叶片角度调整到：{1}%",
    # 多窗帘命令
    0x00010350: "停止多窗帘{0}",
    0x00010351: "打开多窗帘{0}",
    0x00010352: "关闭多窗帘{0}",
    0x00010353: "将多窗帘{0}行程调整到：{1}%",
    0x00010358: "向左旋转多窗帘{0}叶片",
    0x00010359: "向右旋转多窗帘{0}叶片",
    0x0001035A: "停止旋转多窗帘{0}叶片",
    0x0001035B: "将多窗帘{0}叶片角度调整到：{1}%",
    # 窗帘组命令
    0x000103A0: "停止窗帘组【房间：{0}，子组：{1}】",
    0x000103A1: "打开窗帘组【房间：{0}，子组：{1}】",
    0x000103A2: "关闭窗帘组【房间：{0}，子组：{1}】",
    0x000103A3: "将窗帘组【房间：{0}，子组：{1}】行程调整到：{2}%",
    0x000103A8: "向左旋转窗帘组【房间：{0}，子组：{1}】叶片",
    0x000103A9: "向右旋转窗帘组【房间：{0}，子组：{1}】叶片",
    0x000103AA: "停止旋转窗帘组【房间：{0}，子组：{1}】叶片",
    0x000103AB: "将窗帘组【房间：{0}，子组：{1}】叶片角度调整到：{2}%",
    # 单空调命令
    0x00010B00: "关闭单空调{0}",
    0x00010B01: "打开单空调{0}",
    0x00010B02: "将单空调{0}温度调整到：{1}°C",
    0x00010B03: "将单空调{0}工作模式设置为：自动",
    0x00010B04: "将单空调{0}工作模式设置为：制冷",
    0x00010B05: "将单空调{0}工作模式设置为：制热",
    0x00010B06: "将单空调{0}工作模式设置为：送风",
    0x00010B07: "将单空调{0}工作模式设置为：除湿",
    0x00010B08: "将单空调{0}风速模式设置为：自动",
    0x00010B09: "将单空调{0}风速模式设置为：低风",
    0x00010B0A: "将单空调{0}风速模式设置为：中低风",
    0x00010B0B: "将单空调{0}风速模式设置为：中风",
    0x00010B0C: "将单空调{0}风速模式设置为：中高风",
    0x00010B0D: "将单空调{0}风速模式设置为：高风",
    # 空调组命令
    0x00010BA0: "关闭空调组【房间：{0}】",
    0x00010BA1: "打开空调组【房间：{0}】",
    0x00010BA2: "将空调组【房间：{0}】温度调整到：{2}°C",
    0x00010BA3: "将空调组【房间：{0}】工作模式设置为：自动",
    0x00010BA4: "将空调组【房间：{0}】工作模式设置为：制冷",
    0x00010BA5: "将空调组【房间：{0}】工作模式设置为：制热",
    0x00010BA6: "将空调组【房间：{0}】工作模式设置为：送风",
    0x00010BA7: "将空调组【房间：{0}】工作模式设置为：除湿",
    0x00010BA8: "将空调组【房间：{0}】风速模式设置为：自动",
    0x00010BA9: "将空调组【房间：{0}】风速模式设置为：低风",
    0x00010BAA: "将空调组【房间：{0}】风速模式设置为：中低风",
    0x00010BAB: "将空调组【房间：{0}】风速模式设置为：中风",
    0x00010BAC: "将空调组【房间：{0}】风速模式设置为：中高风",
    0x00010BAD: "将空调组【房间：{0}】风速模式设置为：高风",
    # 地暖命令
    0x00011600: "关闭地暖{0}",
    0x00011601: "打开地暖{0}",
    0x00011602: "将地暖{0}温度调整到：{1}°C",
    # 新风命令
    0x00011700: "关闭新风{0}",
    0x00011701: "打开新风{0}",
    0x00011703: "将新风{0}工作模式设置为：自动",
    0x00011704: "将新风{0}工作模式设置为：送风",
    0x00011705: "将新风{0}工作模式设置为：排风",
    0x00011706: "将新风{0}风速模式设置为：自动",
    0x00011707: "将新风{0}风速模式设置为：低风",
    0x00011708: "将新风{0}风速模式设置为：中低风",
    0x00011709: "将新风{0}风速模式设置为：中风",
    0x0001170A: "将新风{0}风速模式设置为：中高风",
    0x0001170B: "将新风{0}风速模式设置为：高风"
}




class Gateway:
    """Class for gateway and managing MQTT connections within the gateway"""
    

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Init dummy hub."""
        self.hass = hass
        self._entry = entry
        self._last_init_time = None
        self.tmp_a19 = None
        
        self._id = entry.data[CONF_NAME]
        
        if "mqttAddr" in entry.data:
            self.mqttAddr = entry.data["mqttAddr"]
            self.mqttAddr1 = entry.data["mqttAddr"]
            if "local" in entry.data :
                self.mqttAddr1 = '+'
            #_LOGGER.warning(f"mqttAddr:{self.mqttAddr}")
        else :
            self.mqttAddr = 0
            self.mqttAddr1 = '+'
        
        
        self.light_group_map = {}

        self.room_map = {}

        self.task_automation_map = {}
           
        self.scene_map = {}
        # self.room_list = []
        self.devTypes = [1, 2, 3, 4, 5, 7, 9, 11 ,16, 20]

        self.reconnect_flag = True

        self.init_state = False

        self.device_map = {}

        self.sns = []

        self.media_player_sn = {}

        self.n_tmp = 10000

        """Lighting Control Type"""
        self.light_device_type = entry.data[CONF_LIGHT_DEVICE_TYPE]

        self.hass.data[MQTT_CLIENT_INSTANCE] = MqttClient(
            self.hass,
            self._entry,
            self._entry.data,
        )

        async def async_stop_mqtt(_event: Event):
            """Stop MQTT component."""
            await self.disconnect()

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, async_stop_mqtt)

    async def reconnect(self, entry: ConfigEntry):
        """Reconnect gateway MQTT"""
        _LOGGER.warning("重新连接 async  reconnect")
        mqtt_client: MqttClient = self.hass.data[MQTT_CLIENT_INSTANCE]
        mqtt_client.conf = entry.data
        await mqtt_client.async_disconnect()
        mqtt_client.init_client()
        await mqtt_client.async_connect()

    async def disconnect(self):
        """Disconnect gateway MQTT connection"""

        mqtt_client: MqttClient = self.hass.data[MQTT_CLIENT_INSTANCE]

        await mqtt_client.async_disconnect()

    async def report_q5_init(self, device_list):
        for device in device_list:
            device_type = device["devType"]
            device["unique_id"] = f"{device['sn']}"

            state = int(device["state"])
            if state == 0:
                continue

            if device_type == 3:
                """Curtain"""
                await self._add_entity("cover", device)
            elif device_type == 1 and self.light_device_type == "single":
                """Light"""
                device["is_group"] = False
                await self._add_entity("button", device)
                await self._add_entity("light", device)
                
            elif device_type == 11:
                """Climate"""
                await self._add_entity("climate", device)
            elif device_type == 4:
                """reboot gateway"""
                await self._add_entity("button", device)
            elif device_type == 7:
                """sensor"""
                if "a121" in device:
                    await self._add_entity("switch", device)
                if "a14" in device:
                    await self._add_entity("sensor", device)
                if "a15" in device:
                    await self._add_entity("binary_sensor", device)
            elif device_type == 16:
                if "a99" in device:
                    await self._add_entity("binary_sensor", device)
            elif device_type == 20:
                if "a41" in device:
                 await self._add_entity("switch", device)
                if "a155" in device and "a158" in device:
                 await self._add_entity("sensor", device)
                
            elif device_type == 9:
                """Constant Temperature Control Panel"""
                a110 = int(device["a110"])
                a111 = int(device["a111"])
                a112 = int(device["a112"])
                if a110 == 1 or a110 == 2 or a111 == 1:
                    await self._add_entity("climate", device)
                if a112 == 1:
                    await self._add_entity("fan", device)
            elif device_type == 2:
                """Switch"""
                if "a15" in device:
                    await self._add_entity("binary_sensor", device)
                if "relays" in device and "relaysNames" in device and "relaysNum" in device:
                    await self._add_entity("switch", device)
                else:
                    self.sns.append(device['sn'])
            elif device_type == 5:
                """MediaPlayer"""
                #self.media_player_sn.append(device['sn'])
                if device['sn'] not in self.media_player_sn:
                    self.media_player_sn[device['sn']] = self.n_tmp 
                    device["num"] = self.n_tmp 
                    await self._add_entity("media_player", device)
                    self.n_tmp  += 1
                else :
                    pass
                
            if "subgroup" in device:
                self.device_map[device['sn']] = {
                    "room": device['room'],
                    "subgroup": device['subgroup']
                }

    async def _async_mqtt_subscribe(self, msg):
        """Process received MQTT messages"""
        #msg = msg.strip()
        payload = msg.payload
        topic = msg.topic
        #_LOGGER.warning(f"topic:{topic} payload:{payload}")


        if payload:
            try:
                payload = json.loads(payload)
                

                # store = Store(self.hass, 1, f'test/{topic}')
                # await store.async_save(payload["data"])
                

            except ValueError:
                _LOGGER.warning("Unable to parse JSON: '%s'", payload)
                return
        else:
            _LOGGER.warning("JSON None")
            return

        if topic.endswith("p5"):
            seq = payload["seq"]
            
            start = payload["data"]["start"]
            count = payload["data"]["count"]
            total = payload["data"]["total"]
            sns_tmp = []
            #_LOGGER.warning(f"q5 data:{payload}")
            model = payload["data"]["list"]
            #for data_tmp in model:
               # if data_tmp["model"] == "ILight2-S1":
                 #   sns_tmp.append(data_tmp['sn'])
            #if sns_tmp:
            # store = Store(self.hass, 1, f'test/model')
           #  await store.async_save(sns_tmp)

            """Device List data"""
            device_list = payload["data"]["list"]

            if seq == 1:
                await self.report_q5_init(device_list)
                if start + count < total:
                    data = {
                        "start": start + count,
                        "max": DEVICE_COUNT_MAX,
                        "devTypes": self.devTypes,
                    }
                    await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q5", data, seq)
            elif seq == 2:

                await self.report_q5_init(device_list)
                if start + count < total:
                    data = {
                        "start": start + count,
                        "max": DEVICE_COUNT_MAX,
                        "sns": self.sns,
                    }
                    await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q5", data, seq)
            elif seq == 3:
                for device in device_list:
                    await self._exec_event_3(device)

        elif topic.endswith("p28"):
            """Scene List data"""
            scene_list = payload["data"]
            room_map = self.room_map
            for scene in scene_list:
                self.scene_map[scene["id"]] = scene["name"]
                scene["unique_id"] = f"{scene['id']}"
                room_id = scene["room"]
                if room_id == 0:
                    scene["room_name"] = "全屋"
                else:
                    scene["room_name"] = room_map.get(
                        room_id, {}).get('name', "未知房间")
                await self._add_entity("scene", scene)

        elif topic.endswith("p71"):
            task_automation_list = payload["data"]
            for task_automation in task_automation_list:
                self.task_automation_map[task_automation["id"]] = task_automation["name"]


        elif topic.endswith("event/3"):
            """Device state data"""
            stats_list = payload["data"]

            string_array = ["sn", "workingTime", "powerSavings"]
            # 过滤不用查询的字段
            string_filter = ["a109", "a15", "travel","relays"]

            string_light_filter = ["on", "rgb", "level", "kelvin"]

            flag = False

            sns = []

            for state in stats_list:
                if any(key in state for key in string_light_filter):
                    flag = True
                    await self._exec_event_3(state)
                    #_LOGGER.warning(f"event/3 data123:{state}")

                elif any(key in state for key in string_filter):
                    await self._exec_event_3(state)
                else:
                    sns.append(state["sn"])

                

                if "workingTime" in state or "powerSavings" in state:
                    for key in state.keys():
                        if key not in string_array:
                            flag = True

            if sns:
                data = {
                    "start": 0,
                    "max": DEVICE_COUNT_MAX,
                    "sns": sns,
                }
                await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q5", data, 3)

            #_LOGGER.warning(f"event/3 data:{payload}")

            if flag:
                await self.sync_group_status(False)
        elif topic.endswith("event/4"):
            _LOGGER.debug(f"event/4 data:{payload}")

        elif topic.endswith("report/q5") or topic.endswith("report/q7"):
            _LOGGER.warning(f"report/q5:{payload}")
            #payload["timestamp"] = timestamp.isoformat()
            message = json.dumps(payload,ensure_ascii=False,indent=4)
            await self.hass.services.async_call( "persistent_notification", "create", {"title":topic,"message": message,"notification_id": topic}, blocking=True)
            

        elif topic.endswith("event/5"):
            group_list = payload["data"]
            _LOGGER.warning(f"event/5 data:{payload}")
            for group in group_list:
                if 'a7' in group and 'a8' in group and 'a9' in group:
                    device_type = group['a7']
                    room_id = group['a8']
                    group_id = group['a9']
                    data = {}
                    if 'a10' in group:
                        data['on'] = group['a10']
                    if 'a11' in group:
                        data['level'] = group['a11']
                    if 'a12' in group:
                        data['kelvin'] = group['a12']
                    if 'a13' in group and group['a13'] != 0:
                        data['rgb'] = group['a13']
                    if device_type == 1 and data:
                        await self._init_or_update_light_group(2, room_id, '', group_id, '', data)

        elif topic.endswith("p33"):
            """Basic data, including room information, light group information, curtain group information"""
            for room in payload["data"]["rooms"]:
                self.room_map[room["id"]] = room
            for lightGroup in payload["data"]["lightsSubgroups"]:
                self.light_group_map[lightGroup["id"]] = lightGroup
            self.room_map[0] = {'id': 0, 'name': '全屋', 'icon': 1}
            self.light_group_map[0] = {'id': 0, 'name': '所有灯', 'icon': 1}

        # elif topic.endswith("p31"):
        #   """Relationship data for rooms and groups"""
        #   self.room_list = []
        #    for room in payload["data"]:
        #        room_id = room["room"]
        #        self.room_list.append(room_id)
        #    await self.sync_group_status(True)
        elif topic.endswith("p55"):
            reversed_dict = {value: key for key, value in self.media_player_sn.items()}
            #_LOGGER.warning(f"p55 reversed_dict:{reversed_dict}")
            
            async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        reversed_dict[payload["seq"]]), payload["data"]
                )
        elif topic.endswith("p82"):
            tmp_lights = {}
            room_map = self.room_map
            light_group_map = self.light_group_map
            seq = payload["seq"]
            if seq == 1 or seq == 2:
             for roomObj in payload["data"] :
                if "a7" in roomObj:
                    room_id = roomObj["a8"]

                    tmp_lights["on"] = roomObj["a10"]

                    tmp_lights["level"] = roomObj["a11"]
                    if "a12" in roomObj:
                        tmp_lights["kelvin"] = roomObj["a12"]

                    if "a13" in roomObj:
                        tmp_lights["rgb"] = roomObj["a13"]

                    lights = tmp_lights
                    room_name = room_map.get(room_id, {}).get('name', "未知房间")
                    light_group_id = roomObj["a9"]
                    light_group_name = light_group_map.get(
                        light_group_id, {}).get('name', "未知灯组")
                    await self._init_or_update_light_group(seq, room_id, room_name, light_group_id,
                                                           light_group_name, lights)

        """
        elif topic.endswith("p51"):
            seq = payload["seq"]

            #gu
            _LOGGER.warning("p51 seq: %s", payload)


            for roomObj in payload["data"]:
                if "lights" in roomObj:
                    room_id = roomObj["id"]
                    lights = roomObj["lights"]
                    room_name = roomObj["name"]
                    light_group_id = 0
                    light_group_name = "所有灯"
                    await self._init_or_update_light_group(seq, room_id, room_name, light_group_id,
                                                           light_group_name, lights)
                    if "subgroups" in lights:
                        for subgroupObj in lights["subgroups"]:
                            light_group_id = int(subgroupObj["id"])
                            light_group_name = subgroupObj["name"]
                            await self._init_or_update_light_group(seq, room_id, room_name, light_group_id,
                                                                   light_group_name, subgroupObj)
        """

    async def _exec_event_3(self, data):
        if "relays" in data:
            for relay, is_on in enumerate(data["relays"]):
                status = {
                    "on": is_on
                }
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        f"switch{data['sn']}{relay}"), status
                )
        # 恒温多实体触发
        elif "devType" in data :
            if data["sn"] == "A4C138A1E1BAE09E":
                self.tmp_a19 = data["a19"]
            if data["devType"] == 9 :
                if self.tmp_a19 is not None:
                    data["a19"] = self.tmp_a19 
                else :
                    data["a19"] = int(data["a19"]) - 9
                #data.pop('a19',None)
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]), data
                )
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"H"), data
                )
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"F"), data
                )
            elif data["devType"] == 16:
                for i, inputname in enumerate(INPUT_SCHEMA,start=1):
                    async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        f"{data['sn']}_{inputname}"), data
                )

            elif data["devType"] == 7 :
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"L"), data
                )
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"M"), data
                )
            elif data["devType"] == 20 :
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]), data
                )

                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"V"), data
                )
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"C"), data
                )
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"E"), data
                )
            else:
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]), data
                )
        elif "a109" in data:
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]), data
                )
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"H"), data
                )
                async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"F"), data
                )

        elif "a15" in data:
            async_dispatcher_send(
                self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                    data["sn"]+"L"), data
            )
            async_dispatcher_send(
                    self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                        data["sn"]+"M"), data
            )

        else:
            async_dispatcher_send(
                self.hass, EVENT_ENTITY_STATE_UPDATE.format(data["sn"]), data
            )

    async def _init_or_update_light_group(self, seq: int, room_id: int, room_name: str, light_group_id: int,
                                          light_group_name: str, light_group: dict):
        if seq == 1:
            group = {
                "unique_id": f"{room_id}-{light_group_id}",
                "room": room_id,
                "subgroup": light_group_id,
                "is_group": True,
                "name": f"{room_name}-{light_group_name}",
            }
            group = dict(light_group, **group)
            await self._add_entity("light", group)
        else:
            await self._event_trigger(room_id, light_group_id, light_group)

    async def _event_trigger(self, room: int, subgroup: int, device: dict):
        state = {}
        if "on" in device:
            state["on"] = int(device["on"])
        if "level" in device:
            state["level"] = float(device["level"])
        if "kelvin" in device:
            state["kelvin"] = int(device["kelvin"])
        if "rgb" in device:
            state["rgb"] = int(device["rgb"])
        async_dispatcher_send(
            self.hass, EVENT_ENTITY_STATE_UPDATE.format(
                f"{room}-{subgroup}"), state
        )

    async def sync_group_status(self, is_init: bool):

        data = [
            {
                "a7": 1
            }
        ]

        """
        for room in self.room_list:
            data.append({
                "id": int(room),
                "lights": {
                    "subgroups": []
                }
            })
        """
        _LOGGER.debug("sync_group_status")
        
        
        if is_init:
            await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q82", data, 1)
            # await self._async_mqtt_publish("P/0/center/q51", data, 1)
        else:
            #延迟15s 刷新
            await asyncio.sleep(15)
            await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q82", data, 2)
           # await self._async_mqtt_publish("P/0/center/q51", data, 2)

    async def _add_entity(self, component: str, device: dict):
        """Add child device information"""
        async_dispatcher_send(
            self.hass, EVENT_ENTITY_REGISTER.format(component), device
        )

    async def init(self, entry: ConfigEntry, is_init: bool):
        """Initialize the gateway business logic, including subscribing to device data, scene data, and basic data,
        and sending data reporting instructions to the gateway"""
        self._entry = entry
        discovery_topics = [
            # Subscribe to device list
            f"{MQTT_TOPIC_PREFIX}/{self.mqttAddr}/center/p5",
            # Subscribe to scene list
            f"{MQTT_TOPIC_PREFIX}/{self.mqttAddr}/center/p28",
            # Subscribe to all basic data Room list, light group list, curtain group list
            f"{MQTT_TOPIC_PREFIX}/{self.mqttAddr}/center/p33",
            f"{MQTT_TOPIC_PREFIX}/{self.mqttAddr}/center/p71",

            f"{MQTT_TOPIC_PREFIX}/{self.mqttAddr}/center/p55",
            # Subscribe to room and light group relationship
            # f"{MQTT_TOPIC_PREFIX}/center/p31",
            # Subscribe to room and light group relationship
            # f"{MQTT_TOPIC_PREFIX}/center/p51",
            # Subscribe to room and light group relationship
            f"{MQTT_TOPIC_PREFIX}/{self.mqttAddr}/center/p82",
            # Subscribe to device property change events
            f"p/{self.mqttAddr1}/event/3",
            #gu
            #"p/+/event/3",
            f"p/{self.mqttAddr1}/event/4",
            f"p/{self.mqttAddr1}/event/5",
            f"p/{self.mqttAddr}/report/q5",
            f"p/{self.mqttAddr}/report/q7",

        ]

       # for subscribe_topic in discovery_topics:
          #  self.hass.data[TEMP_MQTT_TOPIC_PREFIX][subscribe_topic] = True

        try_connect_times = 3

        if self.reconnect_flag:
            await self.reconnect(entry)
            self.reconnect_flag = False
            _LOGGER.warning("重新连接mqtt+++++++++++++++++++++++++++++++++++++++")
        else:
            _LOGGER.warning("没有重新连接mqtt--------------------------------------")

        mqtt_connected = self.hass.data[MQTT_CLIENT_INSTANCE].connected
        while not mqtt_connected:
            await asyncio.sleep(1)
            mqtt_connected = self.hass.data[MQTT_CLIENT_INSTANCE].connected
            _LOGGER.warning("is_init 1 %s mqtt_connected %s",
                            is_init, mqtt_connected)
            try_connect_times = try_connect_times - 1
            if try_connect_times <= 0:
                break

        _LOGGER.warning("is_init 2 %s mqtt_connected %s",
                        is_init, mqtt_connected)
        if mqtt_connected:
            flag = True
            now_time = int(time.time())
            if is_init:
                self._last_init_time = now_time
            else:
                if self._last_init_time is not None:
                    left_time = now_time - self._last_init_time
                    if left_time < 20:
                        return
                else:
                    self._last_init_time = now_time
        else:
            # _LOGGER.warning("repeat scan mdns")
            _LOGGER.warning("未连接，直接退出，等待监控程序检测连接")
            flag = False
            # entry_data = entry.data
            # scanner = MdnsScanner()
            # connection = scanner.scan_single(entry_data[CONF_NAME], 5)
            # if connection is not None:
            #     if CONF_LIGHT_DEVICE_TYPE in entry_data:
            #         connection[CONF_LIGHT_DEVICE_TYPE] = entry_data[CONF_LIGHT_DEVICE_TYPE]
            #         connection["random"] = time.time()
            #     self.hass.config_entries.async_update_entry(
            #         entry,
            #         data=connection,
            #     )

        if flag:
            _LOGGER.warning("start init data")
            self.init_state = True
            try:
                if is_init:

                    await asyncio.gather(
                        *(
                            self.hass.data[MQTT_CLIENT_INSTANCE].async_subscribe(
                                topic,
                                self._async_mqtt_subscribe,
                                0,
                                "utf-8"
                            )
                            for topic in discovery_topics
                        )
                    )
                # publish payload to get all basic data Room list, light group list, curtain group list
                await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q33", {})
                await asyncio.sleep(3)
                # publish payload to get device list
                data = {
                    "start": 0,
                    "max": DEVICE_COUNT_MAX,
                    "devTypes": self.devTypes,
                }
                await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q5", data, 1)
                await asyncio.sleep(3)
                # publish payload to get scene list
                await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q28", {})
                await asyncio.sleep(3)
                await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q71", {})
                
                # await asyncio.sleep(1)

                if self.light_device_type == "group":
                    # publish payload to get room and light group relationship
                    await asyncio.sleep(5)
                    await self.sync_group_status(True)

                    # await self._async_mqtt_publish("P/0/center/q31", {})
                await asyncio.sleep(10)
                if self.sns:
                    data = {
                        "start": 0,
                        "max": DEVICE_COUNT_MAX,
                        "sns": self.sns,
                    }
                    await self._async_mqtt_publish(f"P/{self.mqttAddr}/center/q5", data, 2)
            except OSError as err:
                self.init_state = False
                _LOGGER.error("出了一些问题: %s", err)

    async def async_mqtt_publish(self, topic: str, data: object,n_id = None):
        if n_id is None:
            n_id = 4
        return await self._async_mqtt_publish(topic, data,seq = n_id)

    async def mqtt_subscribe_custom(self, subscribe_topic) -> None:
        await self.hass.data[MQTT_CLIENT_INSTANCE].async_subscribe(
            subscribe_topic,self._async_mqtt_subscribe_custom,0,"utf-8")
        #await self.reconnect(self._entry)
    
    async def _async_mqtt_subscribe_custom(self,msg):
            payload = msg.payload
            topic = msg.topic
            timestamp = msg.timestamp
            
            
            #_LOGGER.warning(f"msg,{msg}")


            if payload:
             try:
                sns_tmp = []
                data_p = {}
                store = Store(self.hass, 1, f'test/model')
                sns_tmp = await store.async_load()
                payload = json.loads(payload)
                seq = payload["seq"]
                if seq == 4 :
                    seq = topic
                if topic.endswith("p86"):
                    payload = self.log_data(payload)
                if topic.endswith("p5") and seq == 88:
                 data_all = payload["data"]["list"]
                 
                 for data_tmp in data_all:
                   data_p["name"] = data_tmp["name"]
                   data_p["sn"] = data_tmp["sn"]
                   data_p["model"] = data_tmp["model"]
                   data_p["state"] = data_tmp["state"]
                   data_p["timestamp"] = timestamp
                   sns_tmp.append(data_p)
                   #if data_tmp["model"] == "ILight2-S1":
                   #   sns_tmp.append(data_tmp['sn'])
                if sns_tmp is not None:
                  await store.async_save(sns_tmp)
                #_LOGGER.warning(f"topic,{topic} payload,{payload}")

                # store = Store(self.hass, 1, f'test/{topic}')
                # await store.async_save(payload["data"])

             except ValueError:
                _LOGGER.warning("Unable to parse JSON: '%s'", payload)
                return
            else:
             _LOGGER.warning("JSON None")
             return
            #payload["timestamp"] = timestamp.isoformat()
            message = json.dumps(payload,ensure_ascii=False,indent=4)
            await self.hass.services.async_call( "persistent_notification", "create", 
             {"title":topic,"message": message,"notification_id": seq}, blocking=True)
  

    async def _async_mqtt_publish(self, topic: str, data: object, seq=2):

        query_device_payload = {
            "seq": seq,
            "rspTo": f"{MQTT_TOPIC_PREFIX}/{self.mqttAddr}",
            "data": data
        }
        #_LOGGER.warning("topic %s data %s", topic, query_device_payload)
        await self.hass.data[MQTT_CLIENT_INSTANCE].async_publish(
            topic,
            json.dumps(query_device_payload),
            0,
            False
        )
    def log_data(self,json_data):
  
    # 确保json_data是字典类型
     if not isinstance(json_data, dict):
        raise ValueError("输入数据必须是字典类型")
    
     data_list = json_data.get('data', {}).get('list', [])
    
     for item in data_list:
        # 获取时间戳
        timestamp = item.get('t')
        data_i = item.get('i')
        data_s_t = item.get('s')
        if data_s_t is not None:
            data_s_t = item.get('s').get('t')
        data_d_t = item.get('d')
        if data_d_t is not None:
            data_d_t = item.get('d').get('t')
        data_r_t = item.get('r')
        if data_r_t is not None:
            data_r_t = item.get('r').get('t')
        #del item['p']
        #del item['r']
        if timestamp is not None:
            # 将Unix时间戳转换为datetime对象，并格式化为字符串
            readable_time = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')  # 使用UTC+8时间
            # 或者使用以下行来获取本地时间：
            item['时间'] = readable_time
            
        if  data_s_t is not None:
            item['s']['t'] = SOURCE_TYPE[data_s_t]
            item['源信息'] = item['s'] 
            del item['s']
        if  data_d_t is not None:
            item['d']['t'] = DESTINATION_TYPE[data_d_t]
            item['目的信息'] = item['d'] 
            del item['d']
        if  data_r_t is not None:
            item['r']['t'] = SOURCE_TYPE[data_r_t]
            item['记录信息'] = item['r'] 
            del item['r']
        if data_i == 0x00000501:
            item['i'] = '自动化执行'
            if self.scene_map is not None and self.task_automation_map is not None:
              _LOGGER.warning(f"场景map{self.scene_map}")
              item['m'][0]= f"{item['m'][0]}-{self.task_automation_map[int(item['m'][0])]}"
              item['m'][1]= f"{item['m'][1]}-{self.scene_map[int(item['m'][1])]}"
        elif data_i == 65953:
            item['i'] = '打开灯组'
            if self.light_group_map is not None:
              _LOGGER.warning(f"灯组map{self.light_group_map}")
              item['m'][0]= f"{item['m'][0]}-{self.room_map[int(item['m'][0])]['name']}"
              item['m'][1]= f"{item['m'][1]}-{self.light_group_map[int(item['m'][1])]['name']}"
        elif data_i == 65952:
            item['i'] = '关闭灯组'
            if self.light_group_map is not None:
              _LOGGER.warning(f"灯组map{self.light_group_map}")
              item['m'][0]= f"{item['m'][0]}-{self.room_map[int(item['m'][0])]['name']}"
              item['m'][1]= f"{item['m'][1]}-{self.light_group_map[int(item['m'][1])]['name']}"
        elif data_i >= 0x000101A2 and data_i <= 0x000101AA:
            item['i'] = '调节灯组'
            if self.light_group_map is not None:
              _LOGGER.warning(f"灯组map{self.light_group_map}")
              item['m'][0]= f"{item['m'][0]}-{self.room_map[int(item['m'][0])]['name']}"
              item['m'][1]= f"{item['m'][1]}-{self.light_group_map[int(item['m'][1])]['name']}"
        elif data_i >= 0x000103A0 and data_i <= 0x000103AB:
            item['i'] = '控制窗帘组'
            if self.room_map is not None:
              item['m'][0]= f"{item['m'][0]}-{self.room_map[int(item['m'][0])]['name']}"
              #item['m'][1]= f"{item['m'][1]}-{self.light_group_map[int(item['m'][1])]['name']}"
        
        elif data_i == 0x00000600 :
             item['i'] = '执行场景'
             item['m'][0]= f"{item['m'][0]}-{self.scene_map[int(item['m'][0])]}"
        
        item['控制'] = item['i']
        item['消息'] = NMNLOG_TEMPLATES[data_i].format(*item['m'])
        
        del item['t']
        del item['m']
        if item.get('u') is not None:
            del item['u']
        if item.get('p') is not None:
            del item['p']
        if item.get('f') is not None:
            del item['f']
        if item.get('i') is not None:
            del item['i']
    
    
     return json_data

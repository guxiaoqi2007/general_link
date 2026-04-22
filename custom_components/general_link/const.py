"""Constants used by multiple MQTT modules."""

DOMAIN = "general_link"

MANUFACTURER = "GeneralLink"

CONF_BROKER = "broker"

CONF_LIGHT_DEVICE_TYPE = "light_device_type"

FLAG_IS_INITIALIZED = "flag_is_initialized"

CACHE_ENTITY_STATE_UPDATE_KEY_DICT = "general_link_entity_state_update_dict"

CONF_ENVKEY = "envkey"

MANUAL_FLAG= "manual_flag"

CONF_PLACE= "place"

EVENT_ENTITY_STATE_UPDATE = "general_link_entity_state_update_{}"

EVENT_ENTITY_REGISTER = "general_link_entity_register_{}"

MQTT_CLIENT_INSTANCE = "mqtt_client_instance"

MQTT_TOPIC_PREFIX = DOMAIN

DEVICE_COUNT_MAX = 100

LOG_REPORT_Q8= "report_q8"

MDNS_SCAN_SERVICE = "_mqtt._tcp.local."

TEMP_MQTT_TOPIC_PREFIX = "general_link_topic_prefix"

PLATFORMS: list[str] = [
    "cover",
    "fan",
    "light",
    "scene",
    "sensor",
    "binary_sensor",
    "switch",
    "climate",
    "media_player",
    "event",
    "button",
    "number",
]
DEVICE_TYPES =  {
    1: "Light",
    2: "Switch",
    3: "Curtain",
    4: "Gateway",
    5: "BackgroundMusic",
    6: "SerialController",          # 或 "SerialDevice"；"Serializer" 在此上下文中不太准确
    7: "Sensor",
    8: "Repeater",
    9: "ThermostatPanel",
    10: "CentralACGateway",
    11: "CentralAC",
    12: "RFGateway",
    13: "RFRemote",
    14: "UniversalIRRemote",
    15: "DimmerKnob",
    16: "DryContact",
    17: "HomeTheater"

}
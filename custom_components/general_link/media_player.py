"""Business logic for light entity."""
from __future__ import annotations

import json
import logging
import homeassistant.util.dt as dt_util
from abc import ABC
from typing import Any
from homeassistant.components import media_source
from homeassistant.components.media_player import MediaPlayerEntity, MediaType, MediaPlayerState, \
    MediaPlayerEntityFeature, RepeatMode,BrowseMedia
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from urllib.parse import urlparse, parse_qs, parse_qsl, quote
from homeassistant.components.media_player.const import (
    MEDIA_CLASS_ALBUM,
    MEDIA_CLASS_ARTIST,
    MEDIA_CLASS_CHANNEL,
    MEDIA_CLASS_DIRECTORY,
    MEDIA_CLASS_EPISODE,
    MEDIA_CLASS_MOVIE,
    MEDIA_CLASS_MUSIC,
    MEDIA_CLASS_PLAYLIST,
    MEDIA_CLASS_SEASON,
    MEDIA_CLASS_TRACK,
    MEDIA_CLASS_TV_SHOW,
    MEDIA_TYPE_ALBUM,
    MEDIA_TYPE_ARTIST,
    MEDIA_TYPE_CHANNEL,
    MEDIA_TYPE_EPISODE,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_PLAYLIST,
    MEDIA_TYPE_SEASON,
    MEDIA_TYPE_TRACK,
    MEDIA_TYPE_TVSHOW,
)

from .const import MQTT_CLIENT_INSTANCE, MANUFACTURER,\
    EVENT_ENTITY_REGISTER, EVENT_ENTITY_STATE_UPDATE,\
    CACHE_ENTITY_STATE_UPDATE_KEY_DICT,MQTT_TOPIC_PREFIX,DOMAIN

_LOGGER = logging.getLogger(__name__)

COMPONENT = "media_player"

CHILD_TYPE_MEDIA_CLASS = {
    MEDIA_TYPE_SEASON: MEDIA_CLASS_SEASON,
    MEDIA_TYPE_ALBUM: MEDIA_CLASS_ALBUM,
    MEDIA_TYPE_MUSIC: MEDIA_CLASS_MUSIC,
    MEDIA_TYPE_ARTIST: MEDIA_CLASS_ARTIST,
    MEDIA_TYPE_MOVIE: MEDIA_CLASS_MOVIE,
    MEDIA_TYPE_PLAYLIST: MEDIA_CLASS_PLAYLIST,
    MEDIA_TYPE_TRACK: MEDIA_CLASS_TRACK,
    MEDIA_TYPE_TVSHOW: MEDIA_CLASS_TV_SHOW,
    MEDIA_TYPE_CHANNEL: MEDIA_CLASS_CHANNEL,
    MEDIA_TYPE_EPISODE: MEDIA_CLASS_EPISODE,
    
}

protocol = 'music://'
class CloudMusicRouter():

    media_source = 'media-source://'
    local_playlist = f'{protocol}local/playlist'

    toplist = f'{protocol}toplist'
    playlist = f'{protocol}playlist'


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """This method is executed after the integration is initialized to create an event listener,
    which is used to create a sub-device"""

    async def async_discover(config_payload):
        try:
            async_add_entities([CustomMediaPlayer(hass, config_payload, config_entry)])
        except Exception:
            raise

    unsub = async_dispatcher_connect(
        hass, EVENT_ENTITY_REGISTER.format(COMPONENT), async_discover
    )

    config_entry.async_on_unload(unsub)


class CustomMediaPlayer(MediaPlayerEntity, ABC):
    """Representation of a MPD server."""

    _attr_media_content_type = MediaType.MUSIC

    # pylint: disable=no-member
    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        """Initialize the MPD device."""
        self._name = config["name"]
        self._attr_unique_id = config["unique_id"]
        self.sn = config["sn"]
        self._model = config["model"]
        self.hass = hass
        self._status = MediaPlayerState.PAUSED
        self._muted = False
        self._volume = False
        self._repeat = RepeatMode.OFF
        self._shuffle = False
        self.mqttAddr = config_entry.data.get("mqttAddr",0)
        self.num = config["num"]
        self.playlist_tmp =[]
        self._media_title = ""
        self._media_artist = None
        self._media_duration = None
        self._media_position = None
        self._media_position_updated_at = None
        self._currentsong = self._media_title
        

        self.update_state(config)
        

        """Add a device state change event listener, and execute the specified method when the device state changes. 
        Note: It is necessary to determine whether an event listener has been added here to avoid repeated additions."""
        key = EVENT_ENTITY_STATE_UPDATE.format(self.unique_id)
        if key not in hass.data[CACHE_ENTITY_STATE_UPDATE_KEY_DICT]:
            unsub = async_dispatcher_connect(
                hass, key, self.async_discover
            )
            hass.data[CACHE_ENTITY_STATE_UPDATE_KEY_DICT][key] = unsub
            config_entry.async_on_unload(unsub)
        self.get_playlist()
    @callback
    def async_discover(self, data: dict) -> None:
        try:
            self.update_state(data)
        except Exception:
            raise
    @property
    def device_info(self) -> DeviceInfo:
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self.sn)},
            "serial_number": self.sn,
            "model": self._model,
            # If desired, the name for the device could be different to the entity
            "name": self._name,
            "manufacturer": MANUFACTURER,
        }

    def update_state(self, data):
        """Light event reporting changes the light state in HA"""
        if  "names" in data:
            self.playlist_tmp = data.get("names", [])
        
        if "playState" in data:
            if data["playState"] == 0:
                self._status = MediaPlayerState.PAUSED
            else:
                self._status = MediaPlayerState.PLAYING

        if "volume" in data:
            self._volume = int(data["volume"] * 100)

        if "silent" in data:
            if data["silent"] == 1:
                self._muted = True
            else:
                self._muted = False
        
        if "playingTime" in data:
            self._media_position = data["playingTime"]
            self._media_position_updated_at = dt_util.utcnow()
        
        if "playingWholeTime" in data:
            self._media_duration = data["playingWholeTime"]
        
        if "playingId" in data:
            if self.playlist_tmp:
                self._media_title = self.playlist_tmp[data["playingId"]].split('-')[-1]
                self._currentsong = self._media_title
                self._media_artist = self.playlist_tmp[data["playingId"]].split('-')[0]
                

        if "playMode" in data:
            if data["playMode"] == 0:
                self._shuffle = False
                self._repeat = RepeatMode.ONE
            elif data["playMode"] == 1:
                self._shuffle = False
                self._repeat = RepeatMode.ALL
            elif data["playMode"] == 2:
                self._repeat = RepeatMode.OFF
                self._shuffle = False
            elif data["playMode"] == 3:
                self._shuffle = True
                self._repeat = RepeatMode.OFF
       
    @property
    def media_duration(self):
        """返回媒体的总时长（单位：秒）"""
        return self._media_duration

    @property
    def media_position(self):
        """返回当前播放的位置（单位：秒）"""
        return self._media_position
    @property
    def media_position_updated_at(self):
        """Last valid time of media position."""
        return self._media_position_updated_at
    @property
    def media_title(self):
        return self._media_title

    @property
    def available(self):
        """Return true if MPD is available and connected."""
        return True

    @property
    def name(self):
        """Return the name of the device."""
        return self._name
    @property
    def media_artist(self):
        """Return the artist of current playing media (Music track only)."""
        return self._media_artist
    @property
    def state(self) -> MediaPlayerState:
        """Return the media state."""
        return self._status

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""

        supported = (
                MediaPlayerEntityFeature.VOLUME_SET
                | MediaPlayerEntityFeature.VOLUME_STEP
                | MediaPlayerEntityFeature.VOLUME_MUTE
                | MediaPlayerEntityFeature.NEXT_TRACK
                | MediaPlayerEntityFeature.PREVIOUS_TRACK
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.PLAY
                | MediaPlayerEntityFeature.PLAY_MEDIA
                | MediaPlayerEntityFeature.REPEAT_SET
                | MediaPlayerEntityFeature.SELECT_SOUND_MODE
                | MediaPlayerEntityFeature.SHUFFLE_SET
                | MediaPlayerEntityFeature.BROWSE_MEDIA
                | MediaPlayerEntityFeature.SEEK
        )

        return supported
    async def async_media_seek(self, position: float) -> None:
        """Send seek command."""
        data = {
            "action": 31,
            "time": int(position)
        }
        self._media_position = position
        self._media_position_updated_at = dt_util.utcnow()
        await self.exec_command(data)
    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume of media player."""
        _LOGGER.warning("async_set_volume_level %s ", volume)
        data = {
            "action": 33,
            "volume": volume
        }
        await self.exec_command(data)
        self._volume = int(volume * 100)

    async def async_volume_up(self) -> None:
        """Service to send the MPD the command for volume up."""
        if self._volume is not None:
            self._volume = self._volume + 5
            if self._volume >= 100:
                self._volume = 100
            _LOGGER.warning("声音加5到  %s", self._volume)
            await self.async_set_volume_level(self._volume / 100)

    async def async_volume_down(self) -> None:
        """Service to send the MPD the command for volume down."""
        if self._volume is not None:
            self._volume = self._volume - 5
            if self._volume <= 0:
                self._volume = 0
            _LOGGER.warning("声音减5到  %s", self._volume)
            await self.async_set_volume_level(self._volume / 100)

    async def async_media_play(self) -> None:
        """Service to send the MPD the command for play/pause."""
        data = {
            "action": 5
        }
        await self.exec_command(data)
        self._status = MediaPlayerState.PLAYING

    async def async_media_pause(self) -> None:
        """Service to send the MPD the command for play/pause."""
        data = {
            "action": 7
        }
        await self.exec_command(data)
        self._status = MediaPlayerState.PAUSED

    async def async_media_next_track(self) -> None:
        """Service to send the MPD the command for next track."""
        _LOGGER.warning("async_media_next_track")
        data = {
            "action": 23
        }
        await self.exec_command(data)
        self._status = MediaPlayerState.PLAYING

    async def async_media_previous_track(self) -> None:
        """Service to send the MPD the command for previous track."""
        _LOGGER.warning("async_media_previous_track")
        data = {
            "action": 21
        }
        await self.exec_command(data)
        self._status = MediaPlayerState.PLAYING

    async def async_browse_media(
        self, media_content_type: str | None = None, media_content_id: str | None = None
    ) -> BrowseMedia:
       # return await media_source.async_browse_media(
       #     self.hass,
       #     media_content_id,
       #     content_filter=lambda item: item.media_content_type.startswith("audio/"),
       # )
       await self.exec_command_playlist({})
        
       if media_content_id in [None, protocol]:
        children = [
            {
                'title': '播放列表',
                'path': CloudMusicRouter.local_playlist,
                'type': MEDIA_TYPE_PLAYLIST
            }
        ]
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=protocol,
            media_content_type=MEDIA_TYPE_CHANNEL,
            title="本地音乐",
            can_play=False,
            can_expand=True,
            children=[],
        )
        for item in children:
            title = item['title']
            media_content_type = item['type']
            media_content_id = item['path']
            if '?' not in media_content_id:
                media_content_id = media_content_id + f'?title={quote(title)}'
            thumbnail = item.get('thumbnail')
           # if thumbnail is not None and 'music.126.net' in thumbnail:
                #thumbnail = cloud_music.netease_image_url(thumbnail)
            library_info.children.append(
                BrowseMedia(
                    title=title,
                    media_class=CHILD_TYPE_MEDIA_CLASS[media_content_type],
                    media_content_type=media_content_type,
                    media_content_id=media_content_id,
                    can_play=False,
                    can_expand=True,
                    thumbnail=thumbnail
                )
            )
        return library_info
       if media_content_id.startswith(CloudMusicRouter.local_playlist):
        # 本地播放列表
        library_info = BrowseMedia(
            media_class=MEDIA_CLASS_DIRECTORY,
            media_content_id=media_content_id,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            title="播放列表",
            can_play=False,
            can_expand=False,
            children=[],
        )

        playlist = [] if hasattr(self, 'playlist') == False else self.playlist
        if self.playlist_tmp is not []:
            playlist = self.playlist_tmp 
        for index, title in enumerate(playlist):
            library_info.children.append(
                BrowseMedia(
                    title=title,
                    media_class=MEDIA_CLASS_MUSIC,
                    media_content_type="MEDIA_TYPE_PLAYLIST",
                    media_content_id=str(index),
                    can_play=True,
                    can_expand=False,
                    thumbnail="https://p1.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg"
                )
            )
        return library_info
    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        #_LOGGER.warning("Playing media: %s, %s, %s", media_type, media_id, kwargs)
        if media_id:
            data = {
                "action": 29,
                "id": int(media_id)
            }
            await self.exec_command(data)
            self._media_title = self.playlist_tmp[int(media_id)].split('-')[-1]
            self._media_artist = self.playlist_tmp[int(media_id)].split('-')[0]
            self._currentsong = self._media_title
    async def async_mute_volume(self, mute: bool) -> None:
        """Mute. Emulated with set_volume_level."""
        if mute:
            data = {
                "action": 35,
                "silent": 1
            }
            await self.exec_command(data)
        else:
            data = {
                "action": 35,
                "silent": 0
            }
            await self.exec_command(data)
        self._muted = mute

    @property
    def repeat(self) -> RepeatMode:
        return self._repeat

    @property
    def volume_level(self):
        """Return the volume level."""
        if self._volume is not None:
            return int(self._volume) / 100
        return None

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Set repeat mode.  关闭时 播放全部歌曲   开启式 """
        _LOGGER.warning("async_set_repeat %s", repeat)
        if repeat == RepeatMode.OFF:
            data = {
                "action": 37,
                "mode": 2
            }
            await self.exec_command(data)
        else:
            if repeat == RepeatMode.ONE:
                data = {
                    "action": 37,
                    "mode": 0
                }
                await self.exec_command(data)
            else:
                data = {
                    "action": 37,
                    "mode": 1
                }
                await self.exec_command(data)
        self._repeat = repeat

    @property
    def shuffle(self):
        """Boolean if shuffle is enabled."""
        return self._shuffle

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Enable/disable shuffle mode."""
        _LOGGER.warning("async_set_shuffle %s", shuffle)
        if shuffle:
            data = {
                "action": 37,
                "mode": 3
            }
            await self.exec_command(data)
        else:
            await self.async_set_repeat(self._repeat)
        self._shuffle = shuffle

    async def exec_command(self, data: dict):

        data["sn"] = self.unique_id

        message = {
            "seq": 1,
            "rspTo": f"{MQTT_TOPIC_PREFIX}/{self.mqttAddr}",
            "data": data
        }

        await self.hass.data[MQTT_CLIENT_INSTANCE].async_publish(
            f"P/{self.mqttAddr}/center/q56",
            json.dumps(message),
            0,
            False
        )
    def get_playlist(self):
        self.hass.async_create_task(self.exec_command_playlist({}))
        
    async def exec_command_playlist(self, data: dict):

        data["sn"] = self.unique_id

        message = {
            "seq": self.num,
            "rspTo": f"{MQTT_TOPIC_PREFIX}/{self.mqttAddr}",
            "data": data
        }

        await self.hass.data[MQTT_CLIENT_INSTANCE].async_publish(
            f"P/{self.mqttAddr}/center/q55",
            json.dumps(message),
            0,
            False
        )

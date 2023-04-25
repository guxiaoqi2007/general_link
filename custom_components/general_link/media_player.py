"""Business logic for light entity."""
from __future__ import annotations

import json
import logging
from abc import ABC
from typing import Any

from homeassistant.components.media_player import MediaPlayerEntity, MediaType, MediaPlayerState, \
    MediaPlayerEntityFeature, RepeatMode
from homeassistant.components.mpd.media_player import PLAYLIST_UPDATE_INTERVAL
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle

from .const import MQTT_CLIENT_INSTANCE, \
    EVENT_ENTITY_REGISTER, EVENT_ENTITY_STATE_UPDATE, CACHE_ENTITY_STATE_UPDATE_KEY_DICT

_LOGGER = logging.getLogger(__name__)

COMPONENT = "media_player"


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

    async_dispatcher_connect(
        hass, EVENT_ENTITY_REGISTER.format(COMPONENT), async_discover
    )


class CustomMediaPlayer(MediaPlayerEntity, ABC):
    """Representation of a MPD server."""

    _attr_media_content_type = MediaType.MUSIC

    # pylint: disable=no-member
    def __init__(self, hass: HomeAssistant, config: dict, config_entry: ConfigEntry) -> None:
        """Initialize the MPD device."""
        self._name = config["name"]
        self._attr_unique_id = config["unique_id"]
        self.sn = config["sn"]

        self._status = MediaPlayerState.PAUSED
        self._currentsong = None
        self._playlists = None
        self._currentplaylist = None
        self._muted = False
        self._volume = False
        self._repeat = RepeatMode.OFF
        self._shuffle = False
        self._commands = None

        self.update_state(config)

        """Add a device state change event listener, and execute the specified method when the device state changes. 
        Note: It is necessary to determine whether an event listener has been added here to avoid repeated additions."""
        key = EVENT_ENTITY_STATE_UPDATE.format(self.unique_id)
        if key not in hass.data[CACHE_ENTITY_STATE_UPDATE_KEY_DICT]:
            hass.data[CACHE_ENTITY_STATE_UPDATE_KEY_DICT][key] = async_dispatcher_connect(
                hass, key, self.async_discover
            )

    @callback
    def async_discover(self, data: dict) -> None:
        try:
            self.update_state(data)
        except Exception:
            raise

    def update_state(self, data):
        """Light event reporting changes the light state in HA"""

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
    def available(self):
        """Return true if MPD is available and connected."""
        return True

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self) -> MediaPlayerState:
        """Return the media state."""
        return self._status

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def media_content_id(self):
        """Return the content ID of current playing media."""
        return "1123"

    @property
    def media_title(self):
        """Return the title of current playing media."""
        name = "name"
        title = "title"

        return f"{name}: {title}"

    @property
    def media_artist(self):
        """Return the artist of current playing media (Music track only)."""
        artists = "纠结伦"
        return artists

    @property
    def media_album_name(self):
        """Return the album of current playing media (Music track only)."""
        return "默认播放器"

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
                | MediaPlayerEntityFeature.SELECT_SOURCE
                | MediaPlayerEntityFeature.SHUFFLE_SET
        )

        return supported

    @property
    def source(self):
        """Name of the current input source."""
        return self._currentplaylist

    @property
    def source_list(self):
        """Return the list of available input sources."""
        return self._playlists

    async def async_select_source(self, source: str) -> None:
        """Choose a different available playlist and play it."""
        await self.async_play_media(MediaType.PLAYLIST, source)

    @Throttle(PLAYLIST_UPDATE_INTERVAL)
    async def _update_playlists(self, **kwargs: Any) -> None:
        """Update available MPD playlists."""
        pass

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

    async def async_play_media(
            self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Send the media player the command for playing a playlist."""
        _LOGGER.warning("async_play_media %s %s %s ", media_type, media_id, kwargs)

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
            "data": data
        }

        await self.hass.data[MQTT_CLIENT_INSTANCE].async_publish(
            "P/0/center/q56",
            json.dumps(message),
            0,
            False
        )

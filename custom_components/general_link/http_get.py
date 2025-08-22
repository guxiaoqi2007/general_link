import asyncio
import logging
import aiohttp
import json
import re
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class HttpRequest:
    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        url: str,
        manufacturer: str,
    ):
        self.hass = hass
        self.username = username
        self.password = password
        self.response_data = None
        self.url = url
        self.headers = {
            "Accept-Language": "zh-CN",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "User-Agent": "okhttp/4.9.3",
        }
        self.params = {
            "appOs": "android",
            "appVersion": "3.9",
            "appVersionNum": "30900",
            "manufacturer": manufacturer,
        }

    async def _send_http_request(
        self,
        url: str,
        method: str,
        params: dict = None,
        headers: dict = None,
        data: str = None,
    ):
        session = async_get_clientsession(self.hass)
        try:
            if method.lower() == "get":
                async with session.get(url, params=params, headers=headers) as response:
                    await self._handle_response(response)
            elif method.lower() == "post":
                async with session.post(
                    url, params=params, headers=headers, data=data
                ) as response:
                    await self._handle_response(response)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Failed to send request: {e}")

    async def _handle_response(self, response):
        if response.status == 200:
            self.response_data = await response.json()
            # _LOGGER.warning("Response: %s", self.response_data)
            """
            set_cookie = response.headers.get("Set-Cookie")
            if set_cookie is not None:
                match = re.search(r'IOT-CLOUD=([^;]+)', set_cookie)
                if match:
                    self.cookie = match.group(1)
                    #self.headers["Cookie"] = self.cookie
            """

        else:
            _LOGGER.error(
                "Failed to get a successful response. Status code: %d", response.status
            )

    # 登陆验证
    async def _server_login(self):
        await self._send_http_request(
            f"https://{self.url}/loginPassword",
            "POST",
            params=self.params,
            headers=self.headers,
            data=f"username={self.username}&password={self.password}",
        )
        # if self.response_data ["code"] == 200:
        #   return True
        # else:
        #  return False

    async def start(self):
        await self._server_login()
        return await self.get_envkey()

    async def get_envkey(self):
        dict_data_by_envKey = {}
        # await self._server_login()
        # response_env  = None

        if self.response_data["code"] == 200:
            await self._send_http_request(
                f"https://{self.url}/env/queryEnvList",
                "GET",
                params=self.params,
                headers=self.headers,
            )
            if self.response_data is not None:
                dict_data_by_envKey = {
                    item["envKey"]: item for item in self.response_data["data"]
                }
                return dict_data_by_envKey
            else:
                _LOGGER.error("Failed to get a successful response.")
                return None
        else:
            return self.response_data

    async def get_backupfile(self, envKey):
        # await self._server_login()
        # response_env  = None
        if self.response_data is None:
            await self._server_login()

        _params = self.params.copy()
        _params["envKey"] = envKey
        _params["orderDesc"] = "true"

        if self.response_data["code"] == 200:
            await self._send_http_request(
                f"https://{self.url}/device-file/getBackupFileList",
                "GET",
                params=_params,
                headers=self.headers,
            )
            if self.response_data is not None:
                return self.response_data
            else:
                _LOGGER.error("Failed to get a successful response.")
                return None


class NetmoonMusicClient:
    def __init__(self, ip_address, session: aiohttp.ClientSession):
        self.base_url = f"http://{ip_address}:8080/service"
        self.session = session
        self.token = None  # 存储登录后获取的token

    async def _make_authenticated_request(self, method, endpoint, data=None):
        """辅助方法：发送带认证的请求"""
        if not self.token:
            raise ValueError("Not logged in. Call login() first.")

        url = f"{self.base_url}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}"}
        kwargs = {"headers": headers}

        if method.upper() == "POST" and data is not None:
            kwargs["data"] = json.dumps(data)
            headers["Content-Type"] = "application/json"

        try:
            async with self.session.request(method.upper(), url, **kwargs) as response:
                resp_json = await response.json()
                if resp_json.get("code") == 200:
                    return resp_json.get("data", {})
                elif resp_json.get("code") == 401:
                    await self.logout()
        except aiohttp.ClientError as e:
            print(f"Network error: {e}")
            return {"code": 500, "msg": str(e)}

    async def login(self, password: str):
        """登录并获取 token"""
        url = f"{self.base_url}/login"
        payload = json.dumps({"password": password})
        headers = {"Content-Type": "application/json"}
        try:
            async with self.session.post(
                url, data=payload, headers=headers
            ) as response:
                resp_json = await response.json()
                if response.status == 200 and resp_json.get("code") == 200:
                    self.token = resp_json["data"]["token"]
                    return True, resp_json["msg"]
                else:
                    return False, resp_json.get("msg", "Login failed")
        except aiohttp.ClientError as e:
            return False, f"Network error: {e}"

    async def is_set_password(self):
        """查询是否已设置密码"""
        url = f"{self.base_url}/is_set_password"
        try:
            async with self.session.get(url) as response:
                return await response.json()
        except aiohttp.ClientError as e:
            print(f"Network error: {e}")
            return {"code": 500, "msg": str(e)}

    async def set_password(self, password: str):
        """初始化密码"""
        url = f"{self.base_url}/set_password"
        payload = json.dumps({"password": password})
        headers = {"Content-Type": "application/json"}
        try:
            async with self.session.post(
                url, data=payload, headers=headers
            ) as response:
                return await response.json()
        except aiohttp.ClientError as e:
            print(f"Network error: {e}")
            return {"code": 500, "msg": str(e)}

    async def set_headphone_volume(self, volume: int):
        """设置设备本地音量"""
        return await self._make_authenticated_request(
            "POST", "set_headphone_volume", {"volume": volume}
        )

    async def get_play_mode_list(self):
        """获取支持的模式"""
        return await self._make_authenticated_request("GET", "get_play_mode_list")

    async def get_device_info(self):
        """获取设备信息"""
        return await self._make_authenticated_request("GET", "get_device_info")

    async def set_play_mode(self, play_mode: str):
        """设置设备模式"""
        return await self._make_authenticated_request(
            "POST", "set_play_mode", {"play_mode": play_mode}
        )

    async def reload_sd_card_playlist(self):
        """SD卡模式下重载资源"""
        return await self._make_authenticated_request("POST", "reload_sd_card_playlist")

    async def get_sd_card_playlist(self):
        """SD卡模式下获取播放列表"""
        return await self._make_authenticated_request("GET", "get_sd_card_playlist")

    async def sd_card_cmd(
        self,
        action: str,
        num: int = None,
        state: int = None,
        mode: int = None,
        seek: int = None,
        vol: int = None,
    ):
        """SD卡模式下操作指令"""
        payload = {"action": action}
        if num is not None:
            payload["num"] = num
        if state is not None:
            payload["state"] = state
        if mode is not None:
            payload["mode"] = mode
        if seek is not None:
            payload["seek"] = seek
        if vol is not None:
            payload["vol"] = vol
        return await self._make_authenticated_request("POST", "sd_card_cmd", payload)

    async def get_sd_card_state(self):
        """SD卡模式下获取状态"""
        return await self._make_authenticated_request("GET", "get_sd_card_state")

    async def get_network_info(self):
        """获取网络信息"""
        return await self._make_authenticated_request("GET", "get_network_info")

    async def scan_wifi(self):
        """开始扫描WIFI"""
        return await self._make_authenticated_request("POST", "scan_wifi")

    async def get_wifi_list(self):
        """获取WIFI列表"""
        return await self._make_authenticated_request("GET", "get_wifi_list")

    async def connect_wifi(self, ssid: str, password: str = None):
        """连接WIFI"""
        payload = {"ssid": ssid}
        if password:
            payload["password"] = password
        return await self._make_authenticated_request("POST", "connect_wifi", payload)

    async def disable_wifi(self):
        """禁用WIFI"""
        return await self._make_authenticated_request("POST", "disable_wifi")

    async def get_version_info(self):
        """获取版本信息检测升级"""
        return await self._make_authenticated_request("GET", "get_version_info")

    async def upgrade(self, url: str, md5: str):
        """开始执行升级"""
        return await self._make_authenticated_request(
            "POST", "upgrade", {"url": url, "md5": md5}
        )

    async def reset_password(self, password: str):
        """初始化密码"""
        return await self._make_authenticated_request(
            "POST", "reset_password", {"password": password}
        )

    async def get_snapserver_list(self):
        """client模式下连接服务端"""
        return await self._make_authenticated_request("GET", "get_snapserver_list")

    async def connect_snapserver(self, snapserver_host: str):
        """client模式下连接服务端"""
        return await self._make_authenticated_request(
            "POST", "connect_snapserver", {"snapserver_host": snapserver_host}
        )

    async def set_airplay_password(self, airplay_password: str):
        """设置AIRPLAY密码"""
        return await self._make_authenticated_request(
            "POST", "set_airplay_password", {"airplay_password": airplay_password}
        )

    async def get_sd_card_playlists_list(self):
        """获取歌单列表"""
        return await self._make_authenticated_request(
            "GET", "get_sd_card_playlists_list"
        )

    async def rename_playlist(self, playlist: str, name: str):
        """歌单设置别名"""
        return await self._make_authenticated_request(
            "POST", "rename_playlist", {"playlist": playlist, "name": name}
        )

    async def sd_card_play_change_playlist(self, playlist: str, num: int = None):
        """切换歌单"""
        payload = {"playlist": playlist}
        if num is not None:
            payload["num"] = num
        return await self._make_authenticated_request(
            "POST", "sd_card_play_change_playlist", payload
        )

    async def get_sd_card_songs_by_playlist(self, playlist: str):
        """获取指定播放列表歌曲"""
        return await self._make_authenticated_request(
            "GET", "get_sd_card_songs_by_playlist", {"playlist": playlist}
        )

    async def sd_card_add_next_song(self, playlist: str, num: int):
        """添加歌单歌曲到队列下一首"""
        return await self._make_authenticated_request(
            "POST", "sd_card_add_next_song", {"playlist": playlist, "num": num}
        )

    async def set_serial_485_id(self, serial_485_id: int):
        """设置485串口ID"""
        return await self._make_authenticated_request(
            "POST", "set_serial_485_id", {"serial_485_id": serial_485_id}
        )

    async def close(self):
        """关闭客户端会话"""
        await self.session.close()

    async def init_and_login(self, password: str):
        """
        初始化并登录设备。

        流程：
        1. 查询是否已设置密码
        - 若未设置 (code == 201)，则先设置密码
        - 若已设置 (code == 200)，跳过设置
        2. 使用密码登录

        返回:
        (success: bool, message: str)
        """
        # 第一步：查询密码设置状态
        try:
            result = await self.is_set_password()
        except Exception as e:
            return False, f"无法连接设备: {e}"

        if not isinstance(result, dict):
            return False, "设备响应格式错误"

        code = result.get("code")

        if code == 201:
            # 未设置密码，进行初始化设置
            _LOGGER.debug("设备未设置密码，正在初始化...")
            set_result = await self.set_password(password)
            if set_result.get("code") != 200:
                return False, f"密码设置失败: {set_result.get('msg', 'Unknown error')}"
            _LOGGER.info("密码设置成功")
        elif code == 200:
            # 已设置密码，无需操作
            _LOGGER.debug("设备已设置密码，跳过初始化")
        else:
            return False, f"未知响应码 [{code}] 来自 is_set_password: {result.get('msg', '')}"

        # 第二步：登录
        try:
            success, msg = await self.login(password)
            if success:
                return True, "登录成功"
            else:
                return False, f"登录失败: {msg}"
        except Exception as e:
            return False, f"登录时发生错误: {e}"


# 示例使用
async def main():
    async with aiohttp.ClientSession() as session:
        client = NetmoonMusicClient("192.168.1.97", session)

        # 登录
        success, msg = await client.login("1234")
        if not success:
            print(f"Login failed: {msg}")
            return

        print(f"Login success: {msg}")

        # 获取设备信息
        device_info = await client.get_device_info()
        print(f"Device Info: {device_info}")

        # 设置音量
        playlist_result = await client.get_sd_card_playlist()
        print(f"Set Volume Result: {playlist_result}")

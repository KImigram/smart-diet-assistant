"""
百度智能云 菜品识别 API 客户端
Tool Use 核心：图像预处理 → 获取token → 调用识别API → 解析候选结果

百度API工作流程：
1. 用 API Key + Secret Key 换取 access_token（有效期30天，可缓存）
2. 用 access_token 调用菜品识别接口
3. 返回 Top-N 候选菜品 + 置信度 + 预估卡路里
"""
import base64
import time
import requests
from config import BAIDU_API_KEY, BAIDU_SECRET_KEY

# 百度 OAuth 接口
TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
# 菜品识别接口
DISH_API_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v2/dish"

# 允许识别的最大菜品数
TOP_N = 5


class BaiduVisionClient:
    """百度菜品识别客户端"""

    def __init__(self, api_key: str = None, secret_key: str = None):
        self.api_key = api_key or BAIDU_API_KEY
        self.secret_key = secret_key or BAIDU_SECRET_KEY
        self._token = None
        self._token_expire = 0  # token过期时间戳

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.secret_key)

    def _get_token(self) -> str:
        """
        获取 access_token，带缓存（百度token有效期30天）。
        这是百度API的特殊之处：不能直接用API Key调用，必须先换token。
        """
        # 缓存未过期直接返回（提前1天刷新）
        if self._token and time.time() < self._token_expire - 86400:
            return self._token

        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key,
        }
        resp = requests.post(TOKEN_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "access_token" not in data:
            raise Exception(f"获取百度token失败: {data}")
        self._token = data["access_token"]
        self._token_expire = time.time() + data.get("expires_in", 2592000)
        return self._token

    def recognize_dish(self, image_bytes: bytes, top_num: int = TOP_N) -> list[dict]:
        """
        识别菜品图片，返回候选列表。

        参数：
            image_bytes: 图片二进制数据
            top_num: 返回候选数量（百度支持1-5）

        返回：
            [{"name": "宫保鸡丁", "probability": 0.92, "calorie": 180}, ...]
            按置信度从高到低排序
        """
        if not self.available:
            return self._mock_result()

        token = self._get_token()

        # 图片转 base64（百度要求）
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")

        params = {"access_token": token}
        data = {
            "image": img_b64,
            "top_num": top_num,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        resp = requests.post(DISH_API_URL, params=params, data=data,
                             headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        if "error_code" in result:
            raise Exception(f"百度识别失败: {result.get('error_msg', result)}")

        # 解析结果
        candidates = []
        for item in result.get("result", []):
            candidates.append({
                "name": item.get("name", ""),
                "probability": round(float(item.get("probability", 0)), 4),
                "calorie": item.get("calorie", ""),  # 百度返回的是字符串，如"180"
                "has_calorie": item.get("has_calorie", False),
            })
        return candidates

    # ---- Mock 降级 ----

    def _mock_result(self) -> list[dict]:
        return [
            {"name": "宫保鸡丁", "probability": 0.85, "calorie": "180", "has_calorie": True},
            {"name": "辣子鸡", "probability": 0.08, "calorie": "220", "has_calorie": True},
            {"name": "黄焖鸡", "probability": 0.04, "calorie": "200", "has_calorie": True},
        ]


# 全局单例
_client = None


def get_vision_client() -> BaiduVisionClient:
    global _client
    if _client is None:
        _client = BaiduVisionClient()
    return _client

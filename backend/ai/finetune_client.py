"""
本地识别服务客户端

调用：POST http://127.0.0.1:8002/recognize
服务：backend/ai/finetune_server.py（微调API识别菜名 + 基座模型裁决验证，即 test_api.py 双通道流程）
参考实现：项目根目录 test_api.py

流程：图片 base64 → 本地识别服务（微调识别→基座裁决→输出菜名） → 返回菜名字符串
"""
import base64

import requests

from config import FINETUNE_API_URL, FINETUNE_TIMEOUT_SECONDS

# 常见图片格式魔数 → MIME 类型（识别服务落盘需要正确的扩展名）
_MIME_SNIFF = [
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"RIFF", "webp"),
    (b"GIF8", "gif"),
]


def _guess_mime(image_bytes: bytes) -> str:
    """按文件头嗅探图片格式"""
    for magic, mime in _MIME_SNIFF:
        if image_bytes.startswith(magic):
            return mime
    return "png"


class FinetuneVisionClient:
    """本地识别服务客户端（微调 + 基座裁决验证）"""

    def __init__(self, api_url: str = None):
        self.api_url = api_url or FINETUNE_API_URL

    def recognize_dish(self, image_bytes: bytes, top_num: int = 5) -> list[dict]:
        """
        调用本地识别服务获取菜品名称（服务端走完整验证流程）。

        参数：
            image_bytes: 图片二进制数据
            top_num: 保留参数（识别服务每次只返回 1 个菜名）

        返回：
            [{"name": "宫保鸡丁", "probability": 1.0, "calorie": ""}]
        """
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime = _guess_mime(image_bytes)

        payload = {"image_base64": img_b64, "mime": mime}

        # 基座模型推理较慢（加载+裁决约1~2分钟），超时给足
        resp = requests.post(
            self.api_url, json=payload, timeout=FINETUNE_TIMEOUT_SECONDS
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"识别服务返回 {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        name = data.get("name", "").strip()
        if not name:
            raise RuntimeError("识别服务未返回菜名")
        # 基座补充的主要食材描述（如"鸡肉, 米饭, 花生"，不漏掉主食热量信息）
        ingredients = data.get("ingredients", "").strip()
        # 完整验证流程通过后给出的菜名，视为高置信匹配
        return [{"name": name, "probability": 1.0, "calorie": "", "ingredients": ingredients}]


# 全局单例
_client = None


def get_finetune_client() -> FinetuneVisionClient:
    global _client
    if _client is None:
        _client = FinetuneVisionClient()
    return _client

"""
DeepSeek 大模型 API 客户端
DeepSeek 兼容 OpenAI API 格式，支持流式输出(SSE)
文档：https://api-docs.deepseek.com/
"""
import json
import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_MODEL

# 系统提示词：设定 AI 角色和行为约束
SYSTEM_PROMPT = """你是一位专业的注册营养师，名为"小营"，为用户提供个性化的营养饮食建议。

【角色定位】
- 基于用户提供的健康档案、历史饮食记录和食物营养知识回答问题
- 回答简洁、实用、有数据支撑，不编造用户未提供的数据
- 如果信息不足，明确告诉用户需要补充什么

【回答规范】
1. 涉及用户个人数据（摄入热量、营养素、体重等）时，必须引用检索到的真实数据
2. 营养建议要具体：给出食物名称、份量、替代方案
3. 不做医疗诊断，涉及疾病建议就医
4. 用中文回答，语气友好专业

【输出格式】
- 先给出核心结论（1-2句）
- 再给出数据支撑或具体建议
- 必要时用分点列举
"""

DEFAULT_MODEL = LLM_MODEL  # 随 USE_REMOTE_LLM 开关切换：ollama=qwen2.5:7b / DeepSeek=deepseek-chat


class LLMClient:
    """DeepSeek 大模型客户端"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        self.model = DEFAULT_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @property
    def available(self) -> bool:
        """是否配置了 API Key"""
        return bool(self.api_key)

    def chat(self, messages: list[dict], temperature: float = 0.7,
             max_tokens: int = 2000) -> str:
        """
        非流式对话，返回完整回复文本。
        messages: [{"role": "system/user/assistant", "content": "..."}]
        """
        if not self.available:
            return self._mock_reply(messages)

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            return "抱歉，AI 服务响应超时，请稍后重试。"
        except requests.exceptions.RequestException as e:
            return f"AI 服务调用失败：{e}"

    def chat_stream(self, messages: list[dict], temperature: float = 0.7,
                    max_tokens: int = 2000):
        """
        流式对话，生成器逐块产出文本。
        没有 API Key 时返回 Mock 流式回复。
        """
        if not self.available:
            yield from self._mock_stream(messages)
            return

        # 本地 Ollama：走原生 /api/chat 流式接口。
        # OpenAI 兼容层流式输出中文时会按字节截断字符，产生乱码；原生接口按 token 输出，无此问题。
        if "11434" in self.base_url:
            yield from self._ollama_stream(messages, temperature, max_tokens)
            return

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        try:
            resp = requests.post(url, headers=self.headers, json=payload,
                                 stream=True, timeout=60)
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]  # 去掉 "data: "
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        except requests.exceptions.Timeout:
            yield "抱歉，AI 服务响应超时。"
        except requests.exceptions.RequestException as e:
            yield f"AI 服务调用失败：{e}"

    def _ollama_stream(self, messages: list[dict], temperature: float,
                       max_tokens: int):
        """Ollama 原生 /api/chat 流式接口，逐块产出 content 文本"""
        base = self.base_url
        if base.endswith("/v1"):
            base = base[:-len("/v1")]
        url = base.rstrip("/") + "/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            resp = requests.post(url, json=payload, stream=True, timeout=300)
            resp.raise_for_status()
            for raw in resp.iter_lines():
                if not raw:
                    continue
                try:
                    obj = json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if obj.get("done"):
                    break
                content = obj.get("message", {}).get("content", "")
                if content:
                    yield content
        except requests.exceptions.Timeout:
            yield "抱歉，AI 服务响应超时。"
        except requests.exceptions.RequestException as e:
            yield f"AI 服务调用失败：{e}"

    # ---- 结构化营养估算（LLM 补全工具缺口） ----
    # 当菜品识别结果未收录到本地食物库时，
    # 让大模型基于菜名估算每100g营养成分 —— 这是 Agent 的典型兜底模式

    NUTRITION_FIELDS = ["calorie", "protein", "fat", "carb", "fiber", "sodium"]

    def estimate_nutrition(self, dish_name: str) -> dict | None:
        """
        基于菜名让 DeepSeek 估算每100g营养成分。
        返回 {calorie, protein, fat, carb, fiber, sodium}，失败返回 None。
        """
        if not self.available:
            return None

        system_prompt = (
            "你是一名营养师。根据菜名估算该菜品每100克可食部分的营养成分，"
            "必须只输出一个JSON对象，不要输出任何其他文字、解释或Markdown代码块标记。"
            '格式：{"calorie": 数值, "protein": 数值, "fat": 数值, "carb": 数值, "fiber": 数值, "sodium": 数值}\n'
            "单位约定：calorie为千卡(kcal)，protein/fat/carb/fiber为克(g)，sodium为毫克(mg)。\n"
            "估算依据常见烹饪方式的合理数值，热量范围50~800，其余按真实食物成分给出合理估计。"
        )
        user_prompt = f"请估算菜品「{dish_name}」每100克的营养成分。"

        try:
            text = self.chat(
                [{"role": "system", "content": system_prompt},
                 {"role": "user", "content": user_prompt}],
                temperature=0.3, max_tokens=300,
            )
            return LLMClient._parse_nutrition_json(text)
        except Exception:
            return None

    @staticmethod
    def _parse_nutrition_json(text: str) -> dict | None:
        """从LLM回复中提取营养JSON（容错：代码块包裹、多余文字）"""
        import re
        if not text:
            return None
        # 去掉可能的 Markdown 代码块
        text = re.sub(r"```(?:json)?", "", text).strip()
        # 提取第一个 { ... } 块
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

        result = {}
        for field in LLMClient.NUTRITION_FIELDS:
            try:
                v = float(data.get(field, 0) or 0)
                if v < 0:
                    v = 0
                result[field] = v
            except (TypeError, ValueError):
                result[field] = 0.0
        return result

    # ---- Mock 降级（无 API Key 时使用） ----

    def _mock_reply(self, messages: list[dict]) -> str:
        user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                user_msg = m["content"]
                break
        return (
            f"【演示模式·未配置 DeepSeek API Key】\n"
            f"收到你的问题：「{user_msg[:50]}」\n"
            f"配置 DEEPSEEK_API_KEY 环境变量后即可获得真实 AI 回复。\n"
            f"当前已检索到用户档案和饮食数据，正式模式下会基于这些数据给出个性化建议。"
        )

    def _mock_stream(self, messages: list[dict]):
        text = self._mock_reply(messages)
        # 模拟逐字输出
        for i in range(0, len(text), 3):
            yield text[i:i + 3]


# 全局单例
_llm = None


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm

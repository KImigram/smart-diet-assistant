# -*- coding: utf-8 -*-
"""
本地智能识别服务：微调API(8000) + 基座本地权重(裁决验证) 双通道

把 test_api.py 的完整识别流程封装为常驻 HTTP 服务，等待后端请求：
    后端POST图片(base64) → 微调API识别菜名 → 基座模型裁决"是这道菜吗"
    → 输出菜品名给后端 → 后端匹配食物库后返回前端

启动（务必使用包含 torch/transformers 的 GPU 环境）：
    python backend/ai/finetune_server.py

监听：127.0.0.1:8002
接口：POST /recognize
    body: {"image_base64": "图片base64", "mime": "png"}
    resp: {"name": "宫保鸡丁", "judge": "是", "ingredients": "鸡肉, 花生, ..."}
"""
import base64
import json
import os
import tempfile
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests  # noqa: E402  微调API调用（torch_gpu 环境自带）

# ================= 配置 =================
# 微调API（llamafactory-cli api 服务，监听 8000）
API_URL = os.environ.get(
    "MINICPM_FINETUNED_API_URL", "http://127.0.0.1:8000/v1/chat/completions"
)
# 基座模型本地权重（不依赖API，transformers 直接加载）
BASE_MODEL_PATH = os.environ.get(
    "MINICPM_BASE_MODEL_PATH", r"D:\models\MiniCPM-V-4.6"
)
DOWNSAMPLE_MODE = "16x"
HOST = os.environ.get("MINICPM_SERVICE_HOST", "127.0.0.1")
PORT = int(os.environ.get("MINICPM_SERVICE_PORT", "8002"))

# 与 test_api.py 保持一致的 prompt
PROMPT_DISH = "你是一个菜品专家，识别图片中的菜品，只回答菜品名称"
# 裁决用简单直接的是/否判断题（test_api.py 同款，实测基座裁决稳定）
# 注意：不要用双重否定的表述，会把基座绕晕导致误判"是"
PROMPT_JUDGE = "图片中的食物是{name}吗？只回答是或否，不要解释"
PROMPT_BASE_DISH = (
    "请识别图片中的食物。如果它是一道常见中国菜，只回答菜名；"
    "如果不是标准中国菜，简要描述它是什么食物（如：轻食沙拉、鸡胸肉蔬菜碗）。直接回答。"
)
PROMPT_INGREDIENTS = (
    "请仔细观察这张图片，描述其中食物的组成成分，"
    "比如包含了哪些主要食材，不需要说出菜名,只列举你识别出的所有食材，具体一点到食材种类，不用其它解释。"
)

MIME = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "webp": "webp", "bmp": "bmp"}


# ================= 微调API通道（识别菜名） =================

def recognize_api(image_path: str, prompt: str, model: str = "minicpm-v-4.6") -> str:
    """调用 8000 微调API (OpenAI 兼容)"""
    ext = os.path.splitext(image_path)[1].lstrip(".").lower()
    mime = MIME.get(ext, "png")
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/{mime};base64,{img_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": 64,
        "temperature": 0.2,
    }

    resp = requests.post(API_URL, json=payload, timeout=180)
    if resp.status_code != 200:
        raise RuntimeError(f"微调API返回 {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# ================= 基座本地通道（裁决/补识别/食材） =================

_base_model = None
_base_processor = None


def get_base_model():
    """延迟加载基座模型（首次请求时加载，约10~30秒；后续复用单例）"""
    global _base_model, _base_processor
    if _base_model is None:
        from transformers import AutoModelForImageTextToText, AutoProcessor
        print("[基座] 首次请求，正在加载本地权重（约10~30秒）...")
        _base_processor = AutoProcessor.from_pretrained(
            BASE_MODEL_PATH, trust_remote_code=True
        )
        _base_model = AutoModelForImageTextToText.from_pretrained(
            BASE_MODEL_PATH,
            trust_remote_code=True,
            torch_dtype="auto",
            device_map="auto",
        ).eval()
        import torch
        print(f"[基座] 加载完成, 显存 {torch.cuda.memory_allocated()/1024**3:.2f} GB")
    return _base_model, _base_processor


def recognize_base(image_path: str, prompt: str) -> str:
    """基座模型本地权重直接推理（不做API）"""
    import torch
    from PIL import Image
    model, processor = get_base_model()
    image = Image.open(image_path).convert("RGB")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
        downsample_mode=DOWNSAMPLE_MODE,
        max_slice_nums=36,
    ).to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            downsample_mode=DOWNSAMPLE_MODE,
            max_new_tokens=64,
        )
    out_ids = generated_ids[0][len(inputs.input_ids[0]):]
    return processor.batch_decode(
        [out_ids], skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0].strip()


# ================= 识别流程 =================

def recognize_smart(image_path: str) -> dict:
    # 微调API识别菜名
    raw_dish = recognize_api(image_path, PROMPT_DISH)
    # 基座裁决: 是微调说的这道菜吗?
    judge_raw = recognize_base(image_path, PROMPT_JUDGE.format(name=raw_dish))
    if judge_raw.startswith("是"):
        name = raw_dish
    else:
        # 裁决"否" -> 基座自己识别菜名/食物名
        name = recognize_base(image_path, PROMPT_BASE_DISH)
    # 基座补充食材描述
    raw_ings = recognize_base(image_path, PROMPT_INGREDIENTS)
    return {"name": name, "judge": judge_raw, "ingredients": raw_ings}


# ================= HTTP 服务 =================

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") != "/recognize":
            self._json({"error": "接口不存在，请 POST /recognize"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            img_b64 = body.get("image_base64", "")
            mime = str(body.get("mime", "png"))
            if not img_b64:
                self._json({"error": "image_base64 不能为空"}, 400)
                return
            raw = base64.b64decode(img_b64)
        except Exception as e:
            self._json({"error": f"参数解析失败: {e}"}, 400)
            return

        tmp = tempfile.NamedTemporaryFile(
            suffix="." + mime, prefix="ndish_", delete=False
        )
        try:
            tmp.write(raw)
            tmp.close()
            print(f"[SERVE] 收到图片({len(raw)}B)，开始识别...")
            result = recognize_smart(tmp.name)
            print(f"[SERVE] 识别完成: {result['name']} (基座裁决: {result['judge']})")
            self._json(result)
        except Exception as e:
            traceback.print_exc()
            self._json({"error": f"识别失败: {e}"}, 500)
        finally:
            try:
                tmp.close()
                os.unlink(tmp.name)
            except Exception:
                pass

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[SERVE] {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    print("=" * 60)
    print("  本地智能识别服务（微调API + 基座裁决验证）")
    print(f"  微调API: {API_URL}")
    print(f"  基座权重: {BASE_MODEL_PATH}")
    print(f"  监听: http://{HOST}:{PORT}/recognize")
    print("  等待后端请求中...")
    print("=" * 60)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

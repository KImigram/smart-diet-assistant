# -*- coding: utf-8 -*-
"""
本地智能识别: 微调模型(API) + 基座模型(本地权重) 双通道
用法:
    python test_api.py                # 用根目录默认图片
    python test_api.py 图片路径        # 指定其他图片
前置: 8000 API 服务已启动(微调版: llamafactory-cli api --model_name_or_path ... --adapter_name_or_path ...)

识别逻辑:
    1. 微调API识别菜名
    2. 基座模型(本地权重)裁决"是这道菜吗?"
        是 -> 采用微调结果
        否 -> 基座自己识别菜名/食物名
    3. 无论结果, 基座都补充食材描述
"""
import base64
import os
import sys

import requests

API_URL = os.environ.get(
    "TEST_API_URL", "http://127.0.0.1:8000/v1/chat/completions"
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IMG = os.path.join(BASE_DIR, "img_1.png")

# 微调API: 识别菜名
PROMPT_DISH = "你是一个菜品专家，识别图片中的菜品，只回答菜品名称"
# 基座: 裁决用 (是/否判断题)
PROMPT_JUDGE = "图片中的食物是{name}吗？只回答是或否，不要解释"
# 基座: 裁决"否"时, 由基座给出一个菜名/食物名
PROMPT_BASE_DISH = (
    "请识别图片中的食物。如果它是一道常见中国菜，只回答菜名；"
    "如果不是标准中国菜，简要描述它是什么食物（如：轻食沙拉、鸡胸肉蔬菜碗）。直接回答。"
)
# 基座: 食材描述
PROMPT_INGREDIENTS = (
    "请仔细观察这张图片，描述其中食物的组成成分，"
    "比如包含了哪些主要食材，不需要说出菜名,只列举你识别出的所有食材，具体一点到食材种类，不用其它解释。"
)

# 基座模型本地权重(不用API服务, 直接transformers加载)
BASE_MODEL_PATH = r"D:\models\MiniCPM-V-4.6"
DOWNSAMPLE_MODE = "16x"

MIME = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "webp": "webp", "bmp": "bmp"}

# 基座模型全局单例(延迟加载)
_base_model = None
_base_processor = None


# ================= 微调API通道 =================

def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def recognize_api(image_path: str, prompt: str, model: str = "minicpm-v-4.6") -> str:
    """调用 8000 微调API (OpenAI 兼容)"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片不存在: {image_path}")
    ext = os.path.splitext(image_path)[1].lstrip(".").lower()
    mime = MIME.get(ext, "png")
    img_b64 = encode_image(image_path)

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
        raise RuntimeError(f"API 返回 {resp.status_code}: {resp.text[:2000]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# ================= 基座本地通道 =================

def get_base_model():
    """延迟加载基座模型(本地权重, transformers 直接推理)"""
    global _base_model, _base_processor
    if _base_model is None:
        import torch
        from PIL import Image  # noqa: F401  (确保 PIL 可用)
        from transformers import AutoModelForImageTextToText, AutoProcessor
        print("[基座] 加载本地权重, 首次约10~30秒...")
        _base_processor = AutoProcessor.from_pretrained(
            BASE_MODEL_PATH, trust_remote_code=True
        )
        _base_model = AutoModelForImageTextToText.from_pretrained(
            BASE_MODEL_PATH,
            trust_remote_code=True,
            torch_dtype="auto",
            device_map="auto",
        ).eval()
        print(f"[基座] 加载完成, 显存 {torch.cuda.memory_allocated()/1024**3:.2f} GB")
    return _base_model, _base_processor


def recognize_base(image_path: str, prompt: str) -> str:
    """基座模型直接推理(不做API)"""
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


# ================= 主识别逻辑 =================

def recognize_smart(image_path: str) -> dict:
    # 1. 微调API识别菜名
    raw_dish = recognize_api(image_path, PROMPT_DISH)

    # 2. 基座裁决: 是微调说的这道菜吗?
    judge_raw = recognize_base(
        image_path, PROMPT_JUDGE.format(name=raw_dish)
    )
    if judge_raw.startswith("是"):
        name = raw_dish
    else:
        # 裁决"否" -> 基座自己识别菜名/食物名
        name = recognize_base(image_path, PROMPT_BASE_DISH)

    # 3. 基座补充食材描述
    raw_ings = recognize_base(image_path, PROMPT_INGREDIENTS)

    return {
        "name": name,
        "ingredients": raw_ings,
        "judge": judge_raw,
    }


if __name__ == "__main__":
    img = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMG
    print(f"图片: {img}")
    try:
        r = recognize_smart(img)
        print(f"✅ 识别结果: {r['name']}")
        if r["judge"]:
            print(f"   基座裁决: {r['judge']}")
        print(f"🍽️  主要食材: {r['ingredients']}")
    except Exception as e:
        print(f"调用失败: {e}")
        sys.exit(1)

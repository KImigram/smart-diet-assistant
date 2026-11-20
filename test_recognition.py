# -*- coding: utf-8 -*-
r"""
MiniCPM-V 4.6 本地菜品识别测试脚本
====================================
用法（PyCharm 直接运行）:
    1. 把测试图片命名为 img.png 放在脚本同目录
    2. 确认 PyCharm 解释器是 torch_gpu 环境
    3. 右键 Run

命令行用法:
    conda activate torch_gpu
    python test_recognition.py <图片路径>

说明:
    - 模型位置在 D:/models/MiniCPM-V-4.6（modelscope 下载的）
    - 识别结果会打印在控制台，这个脚本就是课设识别模块的原型
    - 按官方 README 使用 AutoModelForImageTextToText + apply_chat_template
"""
import os
import sys
import time

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

# Windows 控制台中文输出兼容（避免 GBK 乱码）
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ================= 配置区 =================
MODEL_PATH = r"D:\models\MiniCPM-V-4.6"        # 模型路径，如与你下载位置不同请修改
PROMPT = "识别图片中的菜品，只回答菜名以及具体食材，不要其它解释"    # 识别提示词
MAX_NEW_TOKENS = 64                             # 最多生成多少 token
DOWNSAMPLE_MODE = "16x"                         # 视觉 token 压缩："16x" 快、"4x" 更精细
# ==========================================


def load_model():
    """加载模型（首次加载约 10~30 秒）"""
    print("正在加载模型，请稍候...")
    t0 = time.time()

    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_PATH,
        trust_remote_code=True,     # MiniCPM-V 需要远程代码
        torch_dtype="auto",         # 按模型配置自动选择精度
        device_map="auto",          # 自动放到 GPU
    ).eval()

    processor = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)

    used = torch.cuda.memory_allocated() / 1024**3
    print(f"模型加载完成，耗时 {time.time()-t0:.1f}s，显存占用约 {used:.2f} GB")
    return model, processor


def recognize(model, processor, image_path):
    """识别单张图片中的菜品"""
    image = Image.open(image_path).convert("RGB")
    print(f"图片: {image_path}  尺寸: {image.size}")

    print("识别中...")
    t1 = time.time()

    # 对话消息格式（官方 README 用法）
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": PROMPT},
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
        max_slice_nums=36,          # 高分图切片数，官方图片推荐 36
    ).to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            downsample_mode=DOWNSAMPLE_MODE,
            max_new_tokens=MAX_NEW_TOKENS,
        )

    # 去掉输入部分，只留模型生成的内容
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    answer = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]

    print(f"识别耗时: {time.time()-t1:.1f}s")
    print("=" * 45)
    print(f"识别结果: {answer}")
    print("=" * 45)
    return answer


def main():
    # 默认图片：脚本同目录下的 img.png（PyCharm 直接运行即可）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_image = os.path.join(script_dir, "img_1.png")
    image_path = sys.argv[1] if len(sys.argv) > 1 else default_image

    if not os.path.exists(image_path):
        print(f"图片不存在: {image_path}")
        print("请把测试图片命名为 img.png 放到脚本同目录下，或用命令行参数指定图片路径")
        sys.exit(1)

    if not torch.cuda.is_available():
        print("未检测到 CUDA GPU，请确认 torch_gpu 环境下运行")
        sys.exit(1)

    model, processor = load_model()
    recognize(model, processor, image_path)


if __name__ == "__main__":
    main()

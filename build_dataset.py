# -*- coding: utf-8 -*-
"""
构建 MiniCPM-V 微调数据集: ChineseFoodNet val → LLaMA-Factory sharegpt jsonl
流程: 读208类名 → 生成编号映射到数据集目录 → 每类抽样+坏图过滤 → train/val划分 → 写jsonl
用法: python build_dataset.py
"""
import json
import os
import random
from collections import Counter
from pathlib import Path

from PIL import Image

CLASSES_FILE = r"D:\my program\Python work\smart_diet\chinesefoodnet_classes.txt"
VAL_DIR = Path(r"D:\DataSet\dataset_release\release_data\val")
MAP_OUT = Path(r"D:\my program\Python work\smart_diet\class_mapping.txt")
OUT_DIR = Path(r"D:\my program\Python work\smart_diet\dataset")

PER_CLASS = 20       # 每类抽样张数
TRAIN_SPLIT = 18     # 每类 train 张数(其余为 val)
SEED = 42
MIN_SIDE = 50        # 坏图过滤: 短边最小像素

random.seed(SEED)


def load_classes(path: str) -> list:
    names = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
    assert len(names) == 208, f"类名数量 {len(names)} != 208, 检查 {path}"
    return names


def is_valid(img_path: Path) -> bool:
    try:
        with Image.open(img_path) as im:
            im.verify()
        with Image.open(img_path) as im:
            w, h = im.size
        return min(w, h) >= MIN_SIDE
    except Exception:
        return False


def main():
    names = load_classes(CLASSES_FILE)

    # 1. 编号映射文件 → 数据集目录
    with open(MAP_OUT, "w", encoding="utf-8") as f:
        for i, n in enumerate(names):
            f.write(f"{i:03d}\t{n}\n")
    print(f"[1/4] 映射文件已生成: {MAP_OUT} ({len(names)} 类)")

    # 2. 遍历 val 目录抽样 + 坏图过滤
    train_samples, val_samples, dropped = [], [], 0
    for i, dish in enumerate(names):
        cls_dir = VAL_DIR / f"{i:03d}"
        if not cls_dir.is_dir():
            print(f"  警告: 缺类别目录 {cls_dir.name} ({dish})")
            continue
        imgs = [p for p in cls_dir.iterdir()
                if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
        valid = [p for p in imgs if is_valid(p)]
        dropped += len(imgs) - len(valid)
        random.shuffle(valid)
        pick = valid[:PER_CLASS]
        for p in pick[:TRAIN_SPLIT]:
            train_samples.append((p, dish))
        for p in pick[TRAIN_SPLIT:PER_CLASS]:
            val_samples.append((p, dish))
    print(f"[2/4] 抽样完成: train {len(train_samples)} 条 / val {len(val_samples)} 条 / 坏图丢弃 {dropped} 张")

    # 3. sharegpt 格式
    def to_sharegpt(samples):
        return [{
            "conversations": [
                {"from": "human", "value": "<image>\n你是一个菜品专家，识别图片中的菜品，只回答菜品名称"},
                {"from": "gpt", "value": dish},
            ],
            "images": [p.as_posix()],
        } for p, dish in samples]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for fname, samples in (("train.jsonl", train_samples), ("val.jsonl", val_samples)):
        with open(OUT_DIR / fname, "w", encoding="utf-8") as f:
            for it in to_sharegpt(samples):
                f.write(json.dumps(it, ensure_ascii=False) + "\n")

    # 4. 统计
    cnt = Counter(d for _, d in train_samples)
    print(f"[4/4] 完成: train {len(train_samples)} 条 / val {len(val_samples)} 条 / 覆盖 {len(cnt)} 类")
    for fname in ("train.jsonl", "val.jsonl"):
        fp = OUT_DIR / fname
        print(f"    {fname}: {os.path.getsize(fp)/1e6:.1f} MB, {fp}")


if __name__ == "__main__":
    main()

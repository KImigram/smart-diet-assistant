"""
本地 OCR 客户端：基于 RapidOCR(ONNX PaddleOCR)，完全离线。
用于运动记录截图/健康记录截图的文字提取。
"""
import base64
import io
import logging

logger = logging.getLogger("ocr")

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _engine = RapidOCR()
        except Exception as e:
            logger.warning("RapidOCR 初始化失败: %s", e)
            _engine = False
    return _engine if _engine else None


def extract_text_from_base64(image_base64: str) -> list[str]:
    """
    从 base64 图片提取文字，返回按识别顺序排列的文字行列表。
    """
    engine = _get_engine()
    if engine is None:
        return []
    try:
        img_bytes = base64.b64decode(image_base64)
        result, _ = engine(io.BytesIO(img_bytes))
        if not result:
            return []
        return [str(line[1]).strip() for line in result if line[1] and str(line[1]).strip()]
    except Exception as e:
        logger.error("OCR 识别失败: %s", e)
        return []


def extract_text_from_file(file_path: str) -> list[str]:
    """从本地文件提取文字（用于后端测试/调试）"""
    engine = _get_engine()
    if engine is None:
        return []
    try:
        result, _ = engine(file_path)
        if not result:
            return []
        return [str(line[1]).strip() for line in result if line[1] and str(line[1]).strip()]
    except Exception as e:
        logger.error("OCR 识别失败: %s", e)
        return []

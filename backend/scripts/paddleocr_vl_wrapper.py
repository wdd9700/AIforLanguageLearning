#!/usr/bin/env python3
"""
PaddleOCR-VL Wrapper Script
使用 PaddleOCR-VL 0.9B 模型进行文档解析和 OCR 识别
支持 109 种语言，包括中日英手写识别
"""

import sys
import json
import base64
import time
from pathlib import Path
from io import BytesIO

try:
    from PIL import Image
    from paddleocr import PaddleOCR
except ImportError as e:
    print(json.dumps({
        "success": False,
        "error": f"Import error: {str(e)}. Please install: pip install paddleocr pillow"
    }), file=sys.stderr)
    sys.exit(1)


def decode_image(image_data: str) -> Image.Image:
    """解码 Base64 图片数据"""
    try:
        # 移除 data:image/... 前缀（如果存在）
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        return image
    except Exception as e:
        raise ValueError(f"Failed to decode image: {str(e)}")


def run_ocr(image_input, langs: str = "ch", use_angle_cls: bool = True):
    """
    运行 PaddleOCR-VL 识别
    
    Args:
        image_input: PIL Image 或 图片路径
        langs: 语言代码，支持 ch/en/ja/korean 等
        use_angle_cls: 是否使用方向分类器（兼容参数，内部转换为 use_textline_orientation）
    
    Returns:
        dict: 包含识别结果的字典
    """
    start_time = time.time()
    
    try:
        # 初始化 PaddleOCR (支持中日英韩等多语言)
        # PaddleOCR 3.3.1 API: 禁用文档预处理（文档矫正等），只做 OCR
        load_start = time.time()
        ocr = PaddleOCR(
            use_textline_orientation=use_angle_cls,  # 文本行方向识别
            use_doc_orientation_classify=False,  # 禁用文档方向分类
            use_doc_unwarping=False  # 禁用文档矫正（避免处理手写图片时卡死）
        )
        load_time = time.time() - load_start
        
        # 执行 OCR 识别 (PaddleOCR 3.3.1 API: 推荐使用 predict 替代 ocr)
        ocr_start = time.time()
        result = ocr.predict(image_input)
        ocr_time = time.time() - ocr_start
        
        # 调试：打印结果类型和内容
        import sys
        print(f"[DEBUG] Result type: {type(result)}", file=sys.stderr)
        print(f"[DEBUG] Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}", file=sys.stderr)
        print(f"[DEBUG] Result: {result}", file=sys.stderr)
        
        # 解析结果
        if not result or not result[0]:
            return {
                "success": True,
                "text": "",
                "lines": [],
                "load_time": round(load_time, 3),
                "ocr_time": round(ocr_time, 3),
                "total_time": round(time.time() - start_time, 3)
            }
        
        # 提取文本和边界框
        lines = []
        full_text_parts = []
        
        for line in result[0]:
            box = line[0]  # 坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text_info = line[1]  # (文本, 置信度)
            text = text_info[0]
            confidence = text_info[1]
            
            lines.append({
                "text": text,
                "confidence": round(confidence, 4),
                "bbox": {
                    "top_left": box[0],
                    "top_right": box[1],
                    "bottom_right": box[2],
                    "bottom_left": box[3]
                }
            })
            full_text_parts.append(text)
        
        full_text = "\n".join(full_text_parts)
        
        return {
            "success": True,
            "text": full_text,
            "lines": lines,
            "line_count": len(lines),
            "load_time": round(load_time, 3),
            "ocr_time": round(ocr_time, 3),
            "total_time": round(time.time() - start_time, 3)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_time": round(time.time() - start_time, 3)
        }


def main():
    """主函数：从命令行读取图片路径并执行 OCR"""
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python paddleocr_vl_wrapper.py <image_path> [langs] [use_angle_cls]"
        }))
        sys.exit(1)
    
    image_path = sys.argv[1]
    langs = sys.argv[2] if len(sys.argv) > 2 else "ch"
    use_angle_cls = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else True
    
    try:
        # 执行 OCR（直接传递文件路径）
        result = run_ocr(image_path, langs=langs, use_angle_cls=use_angle_cls)
        
        # 输出 JSON 结果
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

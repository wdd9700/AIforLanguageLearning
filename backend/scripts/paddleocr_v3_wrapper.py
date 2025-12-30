"""
PaddleOCR v3.3.1 Wrapper for OCR Recognition
支持多语言手写识别(日文、英文等)
"""
import sys
import json
import base64
import os
from io import BytesIO
from pathlib import Path

def run_ocr(image_input, lang="japan", use_angle_cls=True):
    """
    运行 PaddleOCR v3.3.1 进行文本识别
    
    Args:
        image_input: 图片路径或 Base64 字符串
        lang: 语言代码 (支持: ch, en, japan, korean 等)
        use_angle_cls: 是否使用文本方向分类
    
    Returns:
        dict: OCR 结果
    """
    try:
        from paddleocr import PaddleOCR
        from PIL import Image
        import numpy as np
        
        # 初始化 PaddleOCR (使用 v3.3.1 简化 API)
        # device 参数: 'cpu', 'gpu', 'gpu:0' 等
        ocr = PaddleOCR(
            use_textline_orientation=use_angle_cls,
            lang=lang,
            device='cpu',  # v3.3.1 使用 device 参数
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
        )
        
        # 处理输入
        if image_input.startswith('data:image') or len(image_input) > 500:
            # Base64 输入
            if ',' in image_input:
                image_input = image_input.split(',')[1]
            img_data = base64.b64decode(image_input)
            image = Image.open(BytesIO(img_data))
        else:
            # 文件路径输入
            if not os.path.exists(image_input):
                return {
                    "success": False,
                    "error": f"文件不存在: {image_input}"
                }
            image = image_input
        
        # 执行 OCR (使用 v3.3.1 predict API)
        print(f"DEBUG: 开始 OCR 识别,语言={lang}", file=sys.stderr, flush=True)
        result = ocr.predict(image)
        
        # 解析结果 (PaddleOCR v3.3.1 返回 OCRResult 对象列表)
        ocr_results = []
        
        # result 是一个列表,每个元素是一个页面的 OCRResult 对象
        for page_result in result:
            # OCRResult 是类似字典的对象,包含 dt_polys, rec_texts, rec_scores 等
            dt_polys = page_result.get('dt_polys')
            rec_texts = page_result.get('rec_texts')
            rec_scores = page_result.get('rec_scores')
            
            if dt_polys is not None and rec_texts is not None:
                for i in range(len(dt_polys)):
                    bbox = dt_polys[i]
                    text = rec_texts[i] if i < len(rec_texts) else ""
                    score = rec_scores[i] if rec_scores and i < len(rec_scores) else 0.0
                    
                    ocr_results.append({
                        "text": str(text),
                        "confidence": float(score),
                        "bbox": bbox.tolist() if hasattr(bbox, 'tolist') else bbox
                    })
        
        print(f"DEBUG: 识别完成,找到 {len(ocr_results)} 个文本区域", file=sys.stderr, flush=True)
        
        return {
            "success": True,
            "results": ocr_results,
            "count": len(ocr_results)
        }
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"ERROR: {error_detail}", file=sys.stderr, flush=True)
        return {
            "success": False,
            "error": str(e),
            "traceback": error_detail
        }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "用法: python paddleocr_v3_wrapper.py <image_path_or_base64> [lang] [use_angle_cls]"
        }))
        sys.exit(1)
    
    image_input = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "japan"
    use_angle_cls = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else True
    
    # 语言代码映射 (v3.3.1 支持的语言)
    lang_map = {
        "ch": "ch",  # 简体中文
        "chinese": "ch",
        "en": "en",  # 英文
        "english": "en",
        "japan": "japan",  # 日文
        "japanese": "japan",
        "korean": "korean",  # 韩文
        "french": "french",
        "german": "german",
        "arabic": "arabic",
        "russian": "russian",
    }
    lang = lang_map.get(lang.lower(), lang)
    
    print(f"DEBUG: PaddleOCR v3.3.1 启动", file=sys.stderr, flush=True)
    print(f"DEBUG: 参数 - 语言:{lang}, 角度分类:{use_angle_cls}", file=sys.stderr, flush=True)
    
    result = run_ocr(image_input, lang, use_angle_cls)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""测试 PaddleOCR 3.3.1 输出格式"""
import json
from paddleocr import PaddleOCR

# 初始化
ocr = PaddleOCR(use_textline_orientation=True)

# 识别
image_path = r"E:\projects\AiforForiegnLanguageLearning\testresources\OCRtest.png"
result = ocr.predict(image_path)

# 打印结果结构
print("\n=== Result Structure ===")
print(f"Type: {type(result)}")
print(f"Length: {len(result)}")

if result:
    first_page = result[0]
    print(f"\nFirst page type: {type(first_page)}")
    if isinstance(first_page, dict):
        print(f"Keys: {list(first_page.keys())}")
        
        # 查找文本结果
        for key in first_page.keys():
            if 'text' in key.lower() or 'ocr' in key.lower() or 'rec' in key.lower():
                print(f"\n=== {key} ===")
                print(f"Type: {type(first_page[key])}")
                if isinstance(first_page[key], (list, dict)):
                    print(json.dumps(first_page[key], ensure_ascii=False, indent=2)[:1000])

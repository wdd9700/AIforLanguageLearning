"""
TTS→ASR 音频质量验证
测试 TTS 生成的音频能否被 ASR 正确识别
"""

import subprocess
import json
import base64
from pathlib import Path
import time

# 配置
TTS_PYTHON = r"C:/Users/74090/Miniconda3/envs/torchnb311/python.exe"
TTS_SCRIPT = Path(__file__).parent / "scripts" / "cosyvoice_wrapper.py"
ASR_PYTHON = r"C:/Users/74090/Miniconda3/py313/envs/asr/python.exe"
ASR_SCRIPT = Path(__file__).parent / "scripts" / "faster_whisper_wrapper.py"
TEMP_DIR = Path(__file__).parent / "temp"

# 测试用例
TEST_CASES = [
    {"text": "你好，今天天气怎么样？", "lang": "zh"},
    {"text": "Hello, how are you today?", "lang": "en"},
]

TEMP_DIR.mkdir(exist_ok=True)

print("=" * 70)
print("TTS → ASR 音频质量验证")
print("=" * 70)

for idx, test in enumerate(TEST_CASES, 1):
    print(f"\n测试 {idx}/{len(TEST_CASES)} ({test['lang']})")
    print(f"原文: {test['text']}\n")
    
    audio_path = TEMP_DIR / f"tts_test_{test['lang']}.wav"
    
    # Step 1: TTS 生成
    print("[1/2] TTS 生成音频...")
    tts_cmd = [
        str(TTS_PYTHON),
        str(TTS_SCRIPT),
        "--text", test['text'],
        "--output", str(audio_path)
    ]
    
    tts_start = time.time()
    tts_result = subprocess.run(tts_cmd, capture_output=True, text=True, timeout=60)
    tts_time = time.time() - tts_start
    
    if tts_result.returncode != 0:
        print(f"❌ TTS 失败")
        continue
    
    print(f"✅ TTS 完成 ({tts_time:.2f}s)\n")
    
    # Step 2: ASR 识别
    print("[2/2] ASR 识别...")
    asr_cmd = [
        str(ASR_PYTHON),
        str(ASR_SCRIPT),
        str(audio_path),
        "--model", "small"
    ]
    
    asr_result = subprocess.run(asr_cmd, capture_output=True, text=True, timeout=60)
    
    if asr_result.returncode != 0:
        print(f"❌ ASR 失败")
        continue
    
    asr_output = json.loads(asr_result.stdout)
    recognized = asr_output['text']
    
    print(f"✅ ASR 完成")
    print(f"识别结果: {recognized}\n")
    
    # 对比
    print("对比:")
    print(f"  原文: {test['text']}")
    print(f"  识别: {recognized}")
    
    if test['text'].lower() in recognized.lower() or recognized.lower() in test['text'].lower():
        print("  状态: ✅ 匹配")
    else:
        print("  状态: ⚠️ 部分匹配")
    
    print("\n" + "-" * 70)

print("\n✅ 测试完成")

#!/usr/bin/env python3
"""
TTS → ASR 循环测试脚本
测试目的：
1. 验证 TTS 输出音频质量
2. 测量 ASR 识别准确性
3. 测量端到端延迟（TTS TTFT + 生成时间 + ASR 处理时间）
"""

import os
import sys
import time
import base64
import json
import subprocess
from pathlib import Path

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg): print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")
def print_info(msg): print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")
def print_error(msg): print(f"{Colors.RED}❌ {msg}{Colors.RESET}")
def print_header(msg): print(f"\n{'='*60}\n{msg}\n{'='*60}")

# 配置
PROJECT_ROOT = Path(__file__).parent.parent
TTS_PYTHON = r"C:/Users/74090/Miniconda3/envs/torchnb311/python.exe"
TTS_SCRIPT = PROJECT_ROOT / "env_check" / "run_cosyvoice2_stream_multilang.py"
ASR_PYTHON = r"C:/Users/74090/Miniconda3/py313/envs/asr/python.exe"
ASR_SCRIPT = PROJECT_ROOT / "backend" / "scripts" / "faster_whisper_wrapper.py"
OUTPUT_DIR = PROJECT_ROOT / "testresources" / "tts_asr_loop"

# 测试文本（多语言）
TEST_TEXTS = [
    {
        "text": "Hello, how are you today?",
        "lang": "en",
        "speaker": "中文女",
        "expected_keywords": ["hello", "how", "are", "you", "today"]
    },
    {
        "text": "你好，今天天气怎么样？",
        "lang": "zh",
        "speaker": "中文女",
        "expected_keywords": ["你好", "今天", "天气", "怎么样"]
    },
    {
        "text": "こんにちは、今日はいい天気ですね。",
        "lang": "ja",
        "speaker": "日语男",
        "expected_keywords": ["こんにちは", "今日", "いい", "天気"]
    },
    {
        "text": "The quick brown fox jumps over the lazy dog.",
        "lang": "en",
        "speaker": "英文女",
        "expected_keywords": ["quick", "brown", "fox", "jumps", "lazy", "dog"]
    }
]

def ensure_output_dir():
    """确保输出目录存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print_info(f"输出目录: {OUTPUT_DIR}")

def run_tts(text: str, speaker: str, output_path: Path) -> dict:
    """
    运行 TTS 生成音频
    返回: {"success": bool, "ttft": float, "rtf": float, "duration": float, "audio_path": str}
    """
    print_info(f"TTS 输入: \"{text}\" (speaker={speaker})")
    
    # 准备 JSON 输入
    input_data = {
        "text": text,
        "speaker": speaker
    }
    
    input_json = json.dumps(input_data, ensure_ascii=False)
    
    # 运行 TTS
    start_time = time.time()
    try:
        result = subprocess.run(
            [TTS_PYTHON, str(TTS_SCRIPT)],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8'
        )
        
        total_time = time.time() - start_time
        
        if result.returncode != 0:
            print_error(f"TTS 失败: {result.stderr}")
            return {"success": False, "error": result.stderr}
        
        # 解析输出 JSON
        output = json.loads(result.stdout)
        
        if not output.get("success"):
            print_error(f"TTS 返回失败: {output.get('error')}")
            return {"success": False, "error": output.get("error")}
        
        # 保存音频到文件
        audio_base64 = output["audio"]
        audio_bytes = base64.b64decode(audio_base64)
        
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)
        
        ttft = output.get("ttft", 0)
        rtf = output.get("rtf", 0)
        duration = output.get("duration", 0)
        
        print_success(f"TTS 完成: TTFT={ttft:.3f}s, RTF={rtf:.2f}, 音频时长={duration:.2f}s, 总耗时={total_time:.2f}s")
        print_info(f"音频大小: {len(audio_bytes)/1024:.1f} KB")
        
        return {
            "success": True,
            "ttft": ttft,
            "rtf": rtf,
            "duration": duration,
            "total_time": total_time,
            "audio_path": str(output_path),
            "audio_size": len(audio_bytes)
        }
        
    except subprocess.TimeoutExpired:
        print_error("TTS 超时 (>60s)")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print_error(f"TTS 异常: {e}")
        return {"success": False, "error": str(e)}

def run_asr(audio_path: Path) -> dict:
    """
    运行 ASR 识别音频
    返回: {"success": bool, "text": str, "time": float, "rtf": float}
    """
    print_info(f"ASR 输入: {audio_path.name}")
    
    # 读取音频文件
    with open(audio_path, 'rb') as f:
        audio_bytes = f.read()
    
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    # 准备 JSON 输入
    input_data = {
        "audio": audio_base64
    }
    
    input_json = json.dumps(input_data)
    
    # 运行 ASR
    start_time = time.time()
    try:
        result = subprocess.run(
            [ASR_PYTHON, str(ASR_SCRIPT)],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8'
        )
        
        asr_time = time.time() - start_time
        
        if result.returncode != 0:
            print_error(f"ASR 失败: {result.stderr}")
            return {"success": False, "error": result.stderr}
        
        # 解析输出 JSON
        output = json.loads(result.stdout)
        
        if not output.get("success"):
            print_error(f"ASR 返回失败: {output.get('error')}")
            return {"success": False, "error": output.get("error")}
        
        recognized_text = output["text"]
        rtf = output.get("rtf", 0)
        
        print_success(f"ASR 完成: 耗时={asr_time:.2f}s, RTF={rtf:.2f}")
        print_info(f"识别文本: \"{recognized_text}\"")
        
        return {
            "success": True,
            "text": recognized_text,
            "time": asr_time,
            "rtf": rtf
        }
        
    except subprocess.TimeoutExpired:
        print_error("ASR 超时 (>60s)")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print_error(f"ASR 异常: {e}")
        return {"success": False, "error": str(e)}

def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    计算词错误率 (WER - Word Error Rate)
    简化版本：仅统计完全匹配的词数
    """
    ref_words = set(reference.lower().split())
    hyp_words = set(hypothesis.lower().split())
    
    if not ref_words:
        return 0.0
    
    matched = len(ref_words & hyp_words)
    total = len(ref_words)
    
    accuracy = matched / total
    wer = 1 - accuracy
    
    return wer

def check_keywords(text: str, keywords: list) -> tuple:
    """检查关键词是否出现在识别文本中"""
    text_lower = text.lower()
    matched = [kw for kw in keywords if kw.lower() in text_lower]
    return matched, len(matched) / len(keywords) if keywords else 0

def main():
    print_header("TTS → ASR 循环测试")
    
    # 检查环境
    if not TTS_SCRIPT.exists():
        print_error(f"TTS 脚本不存在: {TTS_SCRIPT}")
        return 1
    
    if not ASR_SCRIPT.exists():
        print_error(f"ASR 脚本不存在: {ASR_SCRIPT}")
        return 1
    
    ensure_output_dir()
    
    # 统计结果
    results = []
    total_tests = len(TEST_TEXTS)
    passed_tests = 0
    
    for idx, test_case in enumerate(TEST_TEXTS, 1):
        print_header(f"测试 {idx}/{total_tests}: {test_case['lang'].upper()}")
        
        text = test_case["text"]
        speaker = test_case["speaker"]
        expected_keywords = test_case["expected_keywords"]
        
        # 生成输出文件名
        audio_filename = f"test_{idx}_{test_case['lang']}.wav"
        audio_path = OUTPUT_DIR / audio_filename
        
        # Step 1: TTS
        print("\n[1/2] TTS 生成音频")
        tts_result = run_tts(text, speaker, audio_path)
        
        if not tts_result["success"]:
            print_error(f"测试 {idx} 失败: TTS 错误")
            results.append({
                "test": idx,
                "text": text,
                "lang": test_case["lang"],
                "passed": False,
                "error": "TTS failed"
            })
            continue
        
        # Step 2: ASR
        print("\n[2/2] ASR 识别音频")
        asr_result = run_asr(audio_path)
        
        if not asr_result["success"]:
            print_error(f"测试 {idx} 失败: ASR 错误")
            results.append({
                "test": idx,
                "text": text,
                "lang": test_case["lang"],
                "passed": False,
                "error": "ASR failed"
            })
            continue
        
        # 分析结果
        recognized_text = asr_result["text"]
        matched_kw, keyword_acc = check_keywords(recognized_text, expected_keywords)
        
        # 端到端延迟
        e2e_latency = tts_result["total_time"] + asr_result["time"]
        
        print("\n" + "="*60)
        print("📊 测试结果分析")
        print("="*60)
        print(f"原始文本:   {text}")
        print(f"识别文本:   {recognized_text}")
        print(f"关键词匹配: {matched_kw} ({keyword_acc*100:.0f}%)")
        print(f"TTS TTFT:   {tts_result['ttft']:.3f}s")
        print(f"TTS RTF:    {tts_result['rtf']:.2f}")
        print(f"ASR 耗时:   {asr_result['time']:.2f}s")
        print(f"ASR RTF:    {asr_result['rtf']:.2f}")
        print(f"端到端延迟: {e2e_latency:.2f}s")
        print("="*60)
        
        # 判断是否通过（关键词准确率 >= 70%）
        passed = keyword_acc >= 0.7
        
        if passed:
            print_success(f"测试 {idx} 通过")
            passed_tests += 1
        else:
            print_error(f"测试 {idx} 失败: 关键词准确率过低 ({keyword_acc*100:.0f}%)")
        
        results.append({
            "test": idx,
            "lang": test_case["lang"],
            "text": text,
            "recognized": recognized_text,
            "keyword_accuracy": keyword_acc,
            "tts_ttft": tts_result["ttft"],
            "tts_rtf": tts_result["rtf"],
            "asr_time": asr_result["time"],
            "asr_rtf": asr_result["rtf"],
            "e2e_latency": e2e_latency,
            "passed": passed
        })
    
    # 总结
    print_header("测试总结")
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"通过率:   {passed_tests/total_tests*100:.0f}%")
    
    if passed_tests == total_tests:
        print_success("所有测试通过！")
        return 0
    else:
        print_error(f"{total_tests - passed_tests} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

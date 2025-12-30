"""
流式性能测试 - ASR/TTS/OCR 实际性能验证
使用正确的命令行方式调用，验证：
- ASR: RTF ~0.14 (CPU + CCD0 亲和)
- TTS: RTF ~0.85 (GPU + bf16 + TRT)
- OCR: 实际延迟
"""

import sys
import time
import subprocess
import base64
from pathlib import Path
import json

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg): print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")
def print_info(msg): print(f"{Colors.CYAN}ℹ️  {msg}{Colors.RESET}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")
def print_error(msg): print(f"{Colors.RED}❌ {msg}{Colors.RESET}")
def print_header(msg): print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}\n{Colors.BOLD}{msg}{Colors.RESET}\n{Colors.BOLD}{'='*70}{Colors.RESET}\n")

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
TESTRESOURCES = PROJECT_ROOT / "testresources"
TEMP_DIR = PROJECT_ROOT / "backend" / "temp"

# 服务配置
ASR_PYTHON = r"C:/Users/74090/Miniconda3/py313/envs/asr/python.exe"
ASR_SCRIPT = PROJECT_ROOT / "backend" / "scripts" / "faster_whisper_wrapper.py"

TTS_PYTHON = r"C:/Users/74090/Miniconda3/envs/torchnb311/python.exe"
TTS_SCRIPT = PROJECT_ROOT / "backend" / "scripts" / "cosyvoice_wrapper.py"

OCR_PYTHON = r"C:/Users/74090/Miniconda3/py313/envs/ocr/python.exe"
OCR_SCRIPT = PROJECT_ROOT / "backend" / "scripts" / "paddleocr_v3_wrapper.py"

def test_asr_performance():
    """测试 ASR 性能 (预期 RTF ~0.14)"""
    print_header("ASR 性能测试 (Faster-Whisper CPU + CCD0)")
    
    # 测试音频
    test_audio = TESTRESOURCES / "test_zero_shot.wav"
    
    if not test_audio.exists():
        print_error(f"测试音频不存在: {test_audio}")
        return None
    
    print_info(f"测试音频: {test_audio.name} ({test_audio.stat().st_size/1024:.1f} KB)")
    
    # 构建命令（与后端一致）
    cmd = [
        str(ASR_PYTHON),
        str(ASR_SCRIPT),
        str(test_audio),
        "--model", "small",
        "--compute-type", "int8",
        "--cpu-threads", "16"
    ]
    
    print_info(f"命令: {' '.join(cmd)}")
    print()
    
    try:
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        total_time = time.time() - start_time
        
        if result.returncode != 0:
            print_error(f"ASR 失败: {result.stderr}")
            return None
        
        # 解析输出
        output = json.loads(result.stdout)
        
        if not output.get('success'):
            print_error(f"ASR 返回失败: {output.get('error')}")
            return None
        
        # 显示结果
        text = output['text']
        duration = output['duration']
        load_time = output['load_time']
        transcribe_time = output['transcribe_time']
        rtf = output['rtf']
        language = output['language']
        
        print_success("ASR 测试成功")
        print(f"  识别文本: {text[:100]}...")
        print(f"  音频时长: {duration:.2f}s")
        print(f"  加载时间: {load_time:.2f}s")
        print(f"  转录时间: {transcribe_time:.2f}s")
        print(f"  RTF: {rtf:.3f}x")
        print(f"  识别语言: {language}")
        print(f"  总耗时: {total_time:.2f}s")
        print()
        
        # 性能评估
        if rtf <= 0.20:
            print_success(f"✓ RTF 性能优秀: {rtf:.3f}x (预期 ~0.14x)")
        elif rtf <= 0.35:
            print_warning(f"⚠️ RTF 性能可接受: {rtf:.3f}x (预期 ~0.14x)")
        else:
            print_error(f"✗ RTF 性能较差: {rtf:.3f}x (预期 ~0.14x)")
        
        return {
            'success': True,
            'duration': duration,
            'load_time': load_time,
            'transcribe_time': transcribe_time,
            'rtf': rtf,
            'language': language,
            'text_length': len(text)
        }
        
    except subprocess.TimeoutExpired:
        print_error("ASR 超时 (>120s)")
        return None
    except Exception as e:
        print_error(f"ASR 异常: {e}")
        return None

def test_tts_performance():
    """测试 TTS 性能 (预期 RTF ~0.85)"""
    print_header("TTS 性能测试 (CosyVoice2 GPU + bf16 + TRT)")
    
    # 测试文本（多种语言）
    test_texts = [
        ("你好，这是语音合成系统的性能测试。人工智能正在改变我们的生活方式。", "zh"),
        ("Hello, this is a performance test of the text-to-speech system.", "en"),
        ("こんにちは、これは音声合成システムのパフォーマンステストです。", "ja"),
    ]
    
    TEMP_DIR.mkdir(exist_ok=True, parents=True)
    
    results = []
    
    for idx, (text, lang) in enumerate(test_texts, 1):
        print_info(f"测试 {idx}/{len(test_texts)} ({lang})")
        print(f"  文本: {text}")
        print()
        
        output_path = TEMP_DIR / f"tts_test_{lang}.wav"
        
        # 构建命令（与后端一致）
        cmd = [
            str(TTS_PYTHON),
            str(TTS_SCRIPT),
            "--text", text,
            "--output", str(output_path),
            "--speed", "1.0"
        ]
        
        try:
            start_time = time.time()
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            total_time = time.time() - start_time
            
            if result.returncode != 0:
                print_error(f"TTS 失败: {result.stderr[:200]}")
                continue
            
            # 解析输出（JSON 在最后一行）
            lines = result.stdout.strip().split('\n')
            json_line = lines[-1]
            output = json.loads(json_line)
            
            if not output.get('success'):
                print_error(f"TTS 返回失败: {output.get('error')}")
                continue
            
            # 读取音频文件
            if not output_path.exists():
                print_error("TTS 输出文件不存在")
                continue
            
            audio_size = output_path.stat().st_size
            
            # 显示结果
            ttft = output.get('ttft', 0)
            rtf = output.get('rtf', 0)
            duration = output.get('duration', 0)
            sample_rate = output.get('sample_rate', 22050)
            
            print_success(f"TTS 成功 ({lang})")
            print(f"  TTFT: {ttft:.3f}s")
            print(f"  RTF: {rtf:.2f}x")
            print(f"  音频时长: {duration:.2f}s")
            print(f"  采样率: {sample_rate} Hz")
            print(f"  文件大小: {audio_size/1024:.1f} KB")
            print(f"  总耗时: {total_time:.2f}s")
            print()
            
            # 性能评估
            if rtf <= 1.0:
                print_success(f"✓ RTF 性能优秀: {rtf:.2f}x (预期 ~0.85x)")
            elif rtf <= 1.5:
                print_warning(f"⚠️ RTF 性能可接受: {rtf:.2f}x (预期 ~0.85x)")
            else:
                print_error(f"✗ RTF 性能较差: {rtf:.2f}x (预期 ~0.85x)")
            
            print()
            
            results.append({
                'lang': lang,
                'ttft': ttft,
                'rtf': rtf,
                'duration': duration,
                'total_time': total_time
            })
            
        except subprocess.TimeoutExpired:
            print_error(f"TTS 超时 ({lang})")
        except Exception as e:
            print_error(f"TTS 异常 ({lang}): {e}")
    
    if results:
        avg_ttft = sum(r['ttft'] for r in results) / len(results)
        avg_rtf = sum(r['rtf'] for r in results) / len(results)
        
        print_header("TTS 平均性能")
        print(f"平均 TTFT: {avg_ttft:.3f}s")
        print(f"平均 RTF: {avg_rtf:.2f}x")
        print()
        
        return {
            'success': True,
            'avg_ttft': avg_ttft,
            'avg_rtf': avg_rtf,
            'results': results
        }
    
    return None

def test_ocr_performance():
    """测试 OCR 性能"""
    print_header("OCR 性能测试 (PaddleOCR v3.3.1)")
    
    # 测试图片
    test_image = TESTRESOURCES / "OCRtest.png"
    
    if not test_image.exists():
        print_error(f"测试图片不存在: {test_image}")
        return None
    
    print_info(f"测试图片: {test_image.name} ({test_image.stat().st_size/1024:.1f} KB)")
    
    # 构建命令（与后端一致 - 位置参数）
    cmd = [
        str(OCR_PYTHON),
        str(OCR_SCRIPT),
        str(test_image),
        "japan",  # 语言参数
        "false"   # use_angle_cls
    ]
    
    print_info(f"命令: {' '.join(cmd)}")
    print()
    
    try:
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        total_time = time.time() - start_time
        
        if result.returncode != 0:
            print_error(f"OCR 失败: {result.stderr[:200]}")
            return None
        
        # 解析输出
        output = json.loads(result.stdout)
        
        if not output.get('success'):
            print_error(f"OCR 返回失败: {output.get('error')}")
            return None
        
        # 显示结果
        results = output.get('results', [])
        count = output.get('count', 0)
        
        # 提取所有文本
        text = ' '.join([r['text'] for r in results])
        avg_confidence = sum([r['confidence'] for r in results]) / len(results) if results else 0
        
        print_success("OCR 测试成功")
        print(f"  识别区域数: {count}")
        print(f"  识别文本: {text[:100]}...")
        print(f"  平均置信度: {avg_confidence:.2f}")
        print(f"  总耗时: {total_time:.2f}s")
        print()
        
        # 性能评估
        if total_time <= 3.0:
            print_success(f"✓ OCR 性能优秀: {total_time:.2f}s")
        elif total_time <= 5.0:
            print_warning(f"⚠️ OCR 性能可接受: {total_time:.2f}s")
        else:
            print_error(f"✗ OCR 性能较差: {total_time:.2f}s")
        
        return {
            'success': True,
            'total_time': total_time,
            'confidence': avg_confidence,
            'text_length': len(text),
            'region_count': count
        }
        
    except subprocess.TimeoutExpired:
        print_error("OCR 超时 (>60s)")
        return None
    except Exception as e:
        print_error(f"OCR 异常: {e}")
        return None

def main():
    print_header("流式性能测试 - 验证实际工作负载下的表现")
    
    results = {}
    
    # 测试 ASR
    asr_result = test_asr_performance()
    if asr_result:
        results['asr'] = asr_result
    
    # 测试 TTS
    tts_result = test_tts_performance()
    if tts_result:
        results['tts'] = tts_result
    
    # 测试 OCR
    ocr_result = test_ocr_performance()
    if ocr_result:
        results['ocr'] = ocr_result
    
    # 总结
    print_header("性能测试总结")
    
    if 'asr' in results:
        print(f"✅ ASR: RTF={results['asr']['rtf']:.3f}x (预期 ~0.14x)")
    else:
        print("❌ ASR: 测试失败")
    
    if 'tts' in results:
        print(f"✅ TTS: 平均 RTF={results['tts']['avg_rtf']:.2f}x (预期 ~0.85x)")
    else:
        print("❌ TTS: 测试失败")
    
    if 'ocr' in results:
        print(f"✅ OCR: 耗时={results['ocr']['total_time']:.2f}s")
    else:
        print("❌ OCR: 测试失败")
    
    print()
    
    # 计算端到端延迟估算
    if 'asr' in results and 'tts' in results:
        # 假设 5 秒音频的端到端流程
        audio_duration = 5.0
        asr_time = audio_duration * results['asr']['rtf'] + results['asr']['load_time']
        llm_time = 3.0  # 假设 LLM 响应时间
        tts_time = results['tts']['avg_ttft'] + 2.0  # TTFT + 部分生成时间
        
        e2e_latency = asr_time + llm_time + tts_time
        
        print_header("端到端延迟估算 (5秒音频)")
        print(f"ASR: {asr_time:.2f}s (音频 {audio_duration}s × RTF {results['asr']['rtf']:.3f})")
        print(f"LLM: {llm_time:.2f}s (假设)")
        print(f"TTS TTFT: {tts_time:.2f}s")
        print(f"总计: {e2e_latency:.2f}s")
        print()
        
        if e2e_latency <= 10.0:
            print_success(f"✓ 端到端延迟优秀: {e2e_latency:.2f}s")
        else:
            print_warning(f"⚠️ 端到端延迟偏高: {e2e_latency:.2f}s")
    
    # 返回退出码
    success_count = len(results)
    total_tests = 3
    
    return 0 if success_count == total_tests else 1

if __name__ == '__main__':
    sys.exit(main())

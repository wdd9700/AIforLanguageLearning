"""
LLM 流式 → TTS → ASR 完整流程测试
手动输入文本给 LM Studio，测试流式 TTS 并用 ASR 验证
测量端到端延迟
"""

import sys
import time
import json
import subprocess
import base64
import requests
from pathlib import Path

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
def print_header(msg): print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}\n{Colors.BOLD}{msg}{Colors.RESET}\n{Colors.BOLD}{'='*60}{Colors.RESET}\n")

# 配置
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
TTS_PYTHON = r"C:/Users/74090/Miniconda3/envs/torchnb311/python.exe"
TTS_SCRIPT = Path(__file__).parent / "scripts" / "cosyvoice_wrapper.py"
ASR_PYTHON = r"C:/Users/74090/Miniconda3/py313/envs/asr/python.exe"
ASR_SCRIPT = Path(__file__).parent / "scripts" / "faster_whisper_wrapper.py"
TEMP_DIR = Path(__file__).parent / "temp"

# 测试场景
TEST_SCENARIOS = [
    {
        "name": "对话场景 - 英文",
        "model": "qwen/qwen3-30b-a3b-2507",
        "prompt": "Tell me a very short story about a cat in 2 sentences.",
        "expected_lang": "en"
    },
    {
        "name": "对话场景 - 中文",
        "model": "qwen/qwen3-30b-a3b-2507",
        "prompt": "用两句话讲一个关于猫的短故事。",
        "expected_lang": "zh"
    },
    {
        "name": "对话场景 - 日文",
        "model": "qwen/qwen3-30b-a3b-2507",
        "prompt": "猫についての短い物語を2文で教えてください。",
        "expected_lang": "ja"
    },
]

def call_llm(model: str, prompt: str) -> tuple[bool, str, float]:
    """
    调用 LM Studio API
    返回: (成功, 响应文本, 延迟)
    """
    print_info(f"调用 LLM: {model}")
    print_info(f"  Prompt: {prompt}")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            LM_STUDIO_URL,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 200
            },
            timeout=90
        )
        
        llm_time = time.time() - start_time
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}", llm_time
        
        data = response.json()
        text = data['choices'][0]['message']['content'].strip()
        
        return True, text, llm_time
        
    except Exception as e:
        return False, str(e), time.time() - start_time

def call_tts(text: str, output_path: Path) -> tuple[bool, dict]:
    """
    调用 TTS 服务
    返回: (成功, 详细信息)
    """
    if not TTS_SCRIPT.exists():
        return False, {'error': 'TTS script not found'}
    
    print_info("调用 TTS 生成音频...")
    print_info(f"  文本: {text[:100]}...")
    
    # 准备输入
    input_data = {
        "text": text,
        "speaker": "default"
    }
    input_json = json.dumps(input_data, ensure_ascii=False)
    
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
        
        if result.returncode != 0:
            return False, {'error': result.stderr[:200]}
        
        # 解析输出
        output = json.loads(result.stdout)
        
        if not output.get('success'):
            return False, {'error': output.get('error', 'Unknown')}
        
        # 保存音频
        audio_base64 = output['audio']
        audio_bytes = base64.b64decode(audio_base64)
        
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)
        
        tts_time = time.time() - start_time
        
        return True, {
            'ttft': output.get('ttft', 0),
            'rtf': output.get('rtf', 0),
            'duration': output.get('duration', 0),
            'total_time': tts_time,
            'audio_size': len(audio_bytes),
            'sample_rate': output.get('sampleRate', 22050)
        }
        
    except subprocess.TimeoutExpired:
        return False, {'error': 'TTS timeout'}
    except Exception as e:
        return False, {'error': str(e)}

def call_asr(audio_path: Path) -> tuple[bool, str, dict]:
    """
    调用 ASR 识别
    返回: (成功, 识别文本, 详细信息)
    """
    if not ASR_SCRIPT.exists():
        return False, '', {'error': 'ASR script not found'}
    
    print_info("调用 ASR 识别音频...")
    
    # 读取音频
    with open(audio_path, 'rb') as f:
        audio_bytes = f.read()
    
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    # 准备输入
    input_data = {
        "audio": audio_base64,
        "language": "auto"
    }
    input_json = json.dumps(input_data)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [ASR_PYTHON, str(ASR_SCRIPT)],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            return False, '', {'error': result.stderr[:200]}
        
        # 解析输出
        output = json.loads(result.stdout)
        
        if not output.get('success'):
            return False, '', {'error': output.get('error', 'Unknown')}
        
        asr_time = time.time() - start_time
        
        return True, output['text'].strip(), {
            'total_time': asr_time,
            'language': output.get('language', 'unknown'),
            'rtf': output.get('rtf', 0)
        }
        
    except subprocess.TimeoutExpired:
        return False, '', {'error': 'ASR timeout'}
    except Exception as e:
        return False, '', {'error': str(e)}

def main():
    print_header("LLM → TTS → ASR 完整流程测试")
    
    # 创建临时目录
    TEMP_DIR.mkdir(exist_ok=True)
    
    results = []
    
    for idx, scenario in enumerate(TEST_SCENARIOS, 1):
        print_header(f"测试 {idx}/{len(TEST_SCENARIOS)}: {scenario['name']}")
        
        # Step 1: LLM 生成文本
        print_info("Step 1: LLM 生成文本")
        llm_success, llm_text, llm_time = call_llm(scenario['model'], scenario['prompt'])
        
        if not llm_success:
            print_error(f"LLM 失败: {llm_text}")
            results.append({'scenario': scenario['name'], 'success': False, 'error': 'LLM failed'})
            continue
        
        print_success(f"LLM 成功 (耗时: {llm_time:.2f}s)")
        print(f"  响应: {llm_text}")
        print()
        
        # Step 2: TTS 生成音频
        print_info("Step 2: TTS 生成音频")
        audio_path = TEMP_DIR / f"test_{idx}.wav"
        tts_success, tts_info = call_tts(llm_text, audio_path)
        
        if not tts_success:
            print_error(f"TTS 失败: {tts_info.get('error', 'Unknown')}")
            results.append({'scenario': scenario['name'], 'success': False, 'error': 'TTS failed'})
            continue
        
        print_success(f"TTS 成功 (TTFT: {tts_info['ttft']:.3f}s, RTF: {tts_info['rtf']:.2f})")
        print_info(f"  音频时长: {tts_info['duration']:.2f}s")
        print_info(f"  音频大小: {tts_info['audio_size']/1024:.1f} KB")
        print()
        
        # Step 3: ASR 识别音频
        print_info("Step 3: ASR 识别音频")
        asr_success, asr_text, asr_info = call_asr(audio_path)
        
        if not asr_success:
            print_error(f"ASR 失败: {asr_info.get('error', 'Unknown')}")
            results.append({'scenario': scenario['name'], 'success': False, 'error': 'ASR failed'})
            continue
        
        print_success(f"ASR 成功 (耗时: {asr_info['total_time']:.2f}s, RTF: {asr_info['rtf']:.2f})")
        print_info(f"  识别语言: {asr_info['language']}")
        print(f"  识别文本: {asr_text}")
        print()
        
        # 计算端到端延迟
        e2e_latency = llm_time + tts_info['ttft'] + asr_info['total_time']
        
        print_success(f"端到端延迟: {e2e_latency:.2f}s")
        print_info(f"  LLM: {llm_time:.2f}s | TTS TTFT: {tts_info['ttft']:.3f}s | ASR: {asr_info['total_time']:.2f}s")
        
        # 记录结果
        results.append({
            'scenario': scenario['name'],
            'success': True,
            'llm_text': llm_text,
            'llm_time': llm_time,
            'tts_info': tts_info,
            'asr_text': asr_text,
            'asr_info': asr_info,
            'e2e_latency': e2e_latency
        })
    
    # 汇总
    print_header("测试汇总")
    
    successful = [r for r in results if r.get('success')]
    
    for idx, result in enumerate(results, 1):
        status = '✅' if result.get('success') else '❌'
        print(f"{status} 测试 {idx}: {result['scenario']}")
        if result.get('success'):
            print(f"    端到端延迟: {result['e2e_latency']:.2f}s")
    
    print()
    print(f"通过率: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.0f}%)")
    
    if successful:
        avg_e2e = sum(r['e2e_latency'] for r in successful) / len(successful)
        avg_llm = sum(r['llm_time'] for r in successful) / len(successful)
        avg_tts_ttft = sum(r['tts_info']['ttft'] for r in successful) / len(successful)
        avg_asr = sum(r['asr_info']['total_time'] for r in successful) / len(successful)
        
        print()
        print_header("平均性能指标")
        print(f"LLM 平均延迟: {avg_llm:.2f}s")
        print(f"TTS 平均 TTFT: {avg_tts_ttft:.3f}s")
        print(f"ASR 平均延迟: {avg_asr:.2f}s")
        print(f"端到端平均延迟: {avg_e2e:.2f}s")
    
    return 0 if len(successful) == len(results) else 1

if __name__ == '__main__':
    sys.exit(main())

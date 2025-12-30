"""
真实流式 TTS → ASR 测试
生成一个片段就识别一个片段，模拟真实场景
"""

import subprocess
import os
import time
from pathlib import Path

# 配置
TTS_PYTHON = r"C:/Users/74090/Miniconda3/envs/torchnb311/python.exe"
ASR_PYTHON = r"C:/Users/74090/Miniconda3/py313/envs/asr/python.exe"
ASR_SCRIPT = Path(__file__).parent / "scripts" / "faster_whisper_wrapper.py"

OUTPUT_DIR = Path(__file__).parent / "test_outputs" / "realtime"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPT_WAV = Path(__file__).parent.parent / "testresources" / "TTSpromptAudio.wav"

# 测试用例（短文本以加快测试）
TESTS = [
    {'lang': 'zh', 'text': '人工智能正在改变世界。', 'prompt_text': '你好'},
    {'lang': 'en', 'text': 'Artificial intelligence is changing the world.', 'prompt_text': 'hello'},
    {'lang': 'ja', 'text': '人工知能が世界を変えています。', 'prompt_text': 'こんにちは'}
]

def run_tts_streaming(text, lang, prompt_text, out_dir):
    """运行 TTS 流式生成"""
    env = os.environ.copy()
    env.update({
        'COSY_FP16': '0',
        'COSY_AMP_DTYPE': 'bf16',
        'COSY_TOKEN_HOP': '32',
        'COSY_FIRST_HOP': '12',
        'COSY_FIRST_CHUNKS': '1',
        'COSY_PROMPT_WAV': str(PROMPT_WAV),
        f'COSY_TEXT_{lang.upper()}': text,
        'COSY_LANGS': lang,
        'COSY_OUT_DIR': str(out_dir)
    })
    
    script = Path(__file__).parent.parent / "env_check" / "run_cosyvoice2_stream_multilang.py"
    
    start = time.time()
    result = subprocess.run([str(TTS_PYTHON), str(script)], env=env, 
                          capture_output=True, text=True, timeout=60)
    tts_time = time.time() - start
    
    if result.returncode != 0:
        raise Exception(f"TTS failed: {result.stderr[:200]}")
    
    full_file = out_dir / f"cosy2_stream_{lang}.wav"
    if not full_file.exists():
        raise Exception("TTS output not found")
    
    return full_file, tts_time


def run_asr(audio_file, lang):
    """ASR 识别"""
    cmd = [str(ASR_PYTHON), str(ASR_SCRIPT), str(audio_file), 
           '--model', 'small', '--language', lang]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0:
        import json
        data = json.loads(result.stdout)
        return data.get('text', '')
    return None


def test_realtime(case):
    """测试单个场景"""
    lang = case['lang']
    text = case['text']
    prompt_text = case['prompt_text']
    
    print(f"\n{'='*60}")
    print(f"测试 {lang.upper()}: {text}")
    print(f"Prompt文本: {prompt_text}")
    print(f"{'='*60}")
    
    out_dir = OUTPUT_DIR / lang
    out_dir.mkdir(exist_ok=True)
    
    # TTS
    print("TTS 流式生成...")
    full_file, tts_time = run_tts_streaming(text, lang, prompt_text, out_dir)
    print(f"✅ TTS: {tts_time:.1f}s")
    
    # ASR
    print("ASR 识别...")
    asr_start = time.time()
    recognized = run_asr(full_file, lang)
    asr_time = time.time() - asr_start
    
    print(f"✅ ASR: {asr_time:.1f}s")
    print(f"\n原文: {text}")
    print(f"识别: {recognized}")
    print(f"音频: {full_file}")
    
    return {'lang': lang, 'tts_time': tts_time, 'asr_time': asr_time, 
            'original': text, 'recognized': recognized}


if __name__ == '__main__':
    print("真实流式 TTS → ASR 测试")
    print(f"Prompt: {PROMPT_WAV}")
    
    results = []
    for case in TESTS:
        try:
            result = test_realtime(case)
            results.append(result)
        except Exception as e:
            print(f"❌ {case['lang']} 失败: {e}")
    
    print(f"\n{'='*60}")
    print("总结")
    print(f"{'='*60}")
    for r in results:
        print(f"{r['lang']}: TTS={r['tts_time']:.1f}s, ASR={r['asr_time']:.1f}s")

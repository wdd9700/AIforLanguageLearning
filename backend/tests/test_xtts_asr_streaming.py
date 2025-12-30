"""
XTTS v2 TTS → ASR 流式测试

与 CosyVoice 测试脚本保持一致的接口，替换后端为 XTTS v2
"""

import subprocess
import wave
import os
import time
from pathlib import Path
from typing import List, Tuple

# 配置
TTS_PYTHON = r"C:/Users/74090/Miniconda3/envs/torchnb311/python.exe"
TTS_SCRIPT = Path(__file__).parent.parent / "env_check" / "run_xtts_stream_multilang.py"

ASR_PYTHON = r"C:/Users/74090/Miniconda3/py313/envs/asr/python.exe"
ASR_SCRIPT = Path(__file__).parent / "scripts" / "faster_whisper_wrapper.py"

OUTPUT_DIR = Path(__file__).parent / "test_outputs" / "xtts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 使用 testresources 中的提示音频
PROMPT_WAV = Path(__file__).parent.parent / "testresources" / "TTSpromptAudio.wav"

# TTS 环境变量
TTS_ENV = {
    'XTTS_PROMPT_WAV': str(PROMPT_WAV),
    'XTTS_TEMPERATURE': '0.75',      # 稍高的温度提升自然度
    'XTTS_LENGTH_PENALTY': '1.0',
    'XTTS_REPETITION_PENALTY': '2.5',  # 稍高的重复惩罚避免重复
    'XTTS_TOP_K': '50',
    'XTTS_TOP_P': '0.85',
}

# 测试文本（与 CosyVoice 测试保持一致）
TEST_CASES = [
    {
        'lang': 'zh',
        'text': '人工智能正在改变我们的生活方式,从语音识别到自然语言处理,技术的进步让人机交互变得越来越自然。',
        'expected_keywords': ['人工智能', '语音识别', '自然语言', '人机交互']
    },
    {
        'lang': 'en',
        'text': 'Artificial intelligence is revolutionizing how we interact with technology, making voice recognition and natural language processing more accurate than ever before.',
        'expected_keywords': ['artificial intelligence', 'technology', 'voice recognition', 'natural language']
    },
    {
        'lang': 'ja',
        'text': '音声認識技術の進歩により、私たちはより自然な方法でコンピュータと対話できるようになりました。',
        'expected_keywords': ['音声認識', '技術', '対話']
    }
]


def generate_tts_streaming(text: str, lang: str, output_prefix: str) -> Tuple[List[Path], float]:
    """TTS 流式生成音频"""
    print(f"  🎤 XTTS 生成中 (lang={lang})...")
    
    # 准备输出目录
    temp_dir = OUTPUT_DIR / f"{output_prefix}_chunks"
    temp_dir.mkdir(exist_ok=True)
    
    # 构建命令
    cmd = [
        str(TTS_PYTHON),
        str(TTS_SCRIPT)
    ]
    
    # 添加环境变量
    env = os.environ.copy()
    env.update(TTS_ENV)
    
    # 根据语言设置文本
    if lang == 'zh':
        env['XTTS_TEXT_ZH'] = text
        env['XTTS_LANGS'] = 'zh'
    elif lang == 'en':
        env['XTTS_TEXT_EN'] = text
        env['XTTS_LANGS'] = 'en'
    elif lang == 'ja':
        env['XTTS_TEXT_JA'] = text
        env['XTTS_LANGS'] = 'ja'
    
    # 设置输出目录
    env['XTTS_OUT_DIR'] = str(temp_dir)
    
    # 执行 TTS
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,  # XTTS 首次加载稍慢
            encoding='utf-8',
            errors='replace'
        )
        generation_time = time.time() - start_time
        
        if result.returncode != 0:
            print(f"  ❌ TTS 失败 (退出码 {result.returncode})")
            print(f"     标准输出: {result.stdout[:800]}")
            print(f"     错误输出: {result.stderr[:800]}")
            return [], generation_time
        
        # 打印完整输出用于调试
        print(f"  📝 TTS 输出预览:")
        for line in result.stdout.split('\n')[:15]:
            if line.strip():
                print(f"     {line}")
        
        # 查找生成的音频文件
        audio_file = temp_dir / f"xtts_stream_{lang}.wav"
        
        if not audio_file.exists():
            print(f"  ⚠️  未找到音频文件: {audio_file.name}")
            print(f"     输出: {result.stdout[:200]}")
            return [], generation_time
        
        print(f"  ✅ 生成完成: {audio_file.name}, 耗时 {generation_time:.2f}s")
        return [audio_file], generation_time
    
    except subprocess.TimeoutExpired:
        print(f"  ❌ TTS 超时 (>180s)")
        return [], 180.0
    except Exception as e:
        print(f"  ❌ TTS 异常: {e}")
        return [], time.time() - start_time


def recognize_asr_streaming(audio_file: Path, lang: str = None) -> Tuple[str, float]:
    """ASR 流式识别音频"""
    print(f"  🎧 ASR 识别中...")
    
    cmd = [
        str(ASR_PYTHON),
        str(ASR_SCRIPT),
        str(audio_file),
        '--model', 'small',
        '--compute-type', 'int8',
        '--cpu-threads', '16'
    ]
    
    if lang:
        lang_map = {'zh': 'zh', 'en': 'en', 'ja': 'ja'}
        if lang in lang_map:
            cmd += ['--language', lang_map[lang]]
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )
        recognition_time = time.time() - start_time
        
        if result.returncode != 0:
            print(f"  ❌ ASR 失败 (退出码 {result.returncode})")
            print(f"     错误输出: {result.stderr[:200]}")
            return "", recognition_time
        
        text = result.stdout.strip()
        
        print(f"  ✅ 识别完成: 耗时 {recognition_time:.2f}s")
        print(f"     文本: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        return text, recognition_time
    
    except subprocess.TimeoutExpired:
        print(f"  ❌ ASR 超时 (>30s)")
        return "", 30.0
    except Exception as e:
        print(f"  ❌ ASR 异常: {e}")
        return "", time.time() - start_time


def check_text_similarity(original: str, recognized: str, keywords: List[str]) -> dict:
    """检查识别文本的准确性"""
    recognized_lower = recognized.lower()
    
    # 检查关键词匹配
    matched_keywords = [kw for kw in keywords if kw.lower() in recognized_lower]
    keyword_coverage = len(matched_keywords) / len(keywords) if keywords else 0
    
    # 简单的字符匹配率
    original_chars = set(original.lower().replace(' ', ''))
    recognized_chars = set(recognized.lower().replace(' ', ''))
    char_overlap = len(original_chars & recognized_chars) / len(original_chars) if original_chars else 0
    
    return {
        'keyword_coverage': keyword_coverage,
        'matched_keywords': matched_keywords,
        'char_overlap': char_overlap,
        'length_ratio': len(recognized) / len(original) if original else 0
    }


def test_tts_asr_streaming(test_case: dict, test_id: int):
    """测试单个 TTS → ASR 流式流程"""
    print(f"\n{'='*80}")
    print(f"测试 {test_id}: {test_case['lang'].upper()} (XTTS v2)")
    print(f"{'='*80}")
    print(f"原始文本: {test_case['text']}\n")
    
    output_prefix = f"test{test_id}_{test_case['lang']}"
    
    # Step 1: TTS 流式生成
    chunk_files, tts_time = generate_tts_streaming(
        test_case['text'],
        test_case['lang'],
        output_prefix
    )
    
    if not chunk_files:
        print("❌ 测试失败: TTS 生成失败\n")
        return None
    
    # Step 2: 合并音频片段（如果只有一个文件则直接复制）
    merged_audio = OUTPUT_DIR / f"{output_prefix}_merged.wav"
    
    if len(chunk_files) == 1:
        import shutil
        shutil.copy2(chunk_files[0], merged_audio)
        file_size = merged_audio.stat().st_size / 1024
        print(f"  ✅ 音频已保存: {merged_audio.name} ({file_size:.1f} KB)")
    else:
        print(f"  ⚠️  多文件合并暂未实现")
        return None
    
    # Step 3: ASR 流式识别
    recognized_text, asr_time = recognize_asr_streaming(merged_audio, test_case['lang'])
    
    if not recognized_text:
        print("❌ 测试失败: ASR 识别失败\n")
        return None
    
    # Step 4: 检查准确性
    similarity = check_text_similarity(
        test_case['text'],
        recognized_text,
        test_case['expected_keywords']
    )
    
    # 生成测试报告
    report = {
        'test_id': test_id,
        'lang': test_case['lang'],
        'original_text': test_case['text'],
        'recognized_text': recognized_text,
        'tts_time': tts_time,
        'asr_time': asr_time,
        'total_time': tts_time + asr_time,
        'audio_file': str(merged_audio),
        'chunk_count': len(chunk_files),
        'similarity': similarity
    }
    
    # 打印结果
    print(f"\n{'─'*80}")
    print("📊 测试结果:")
    print(f"{'─'*80}")
    print(f"  TTS 生成时间: {tts_time:.2f}s ({len(chunk_files)} 个片段)")
    print(f"  ASR 识别时间: {asr_time:.2f}s")
    print(f"  总耗时: {report['total_time']:.2f}s")
    print(f"  音频文件: {merged_audio.absolute()}")
    print(f"\n  原始文本: {test_case['text']}")
    print(f"  识别文本: {recognized_text}")
    print(f"\n  关键词匹配: {similarity['keyword_coverage']*100:.0f}% ({len(similarity['matched_keywords'])}/{len(test_case['expected_keywords'])})")
    print(f"  匹配关键词: {similarity['matched_keywords']}")
    print(f"  字符重叠率: {similarity['char_overlap']*100:.0f}%")
    print(f"  长度比: {similarity['length_ratio']:.2f}")
    
    # 判断测试是否通过
    passed = similarity['keyword_coverage'] >= 0.5
    status = "✅ 通过" if passed else "⚠️ 部分通过"
    print(f"\n  {status}")
    print(f"{'─'*80}\n")
    
    return report


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("XTTS v2 流式生成 → ASR 流式识别 完整测试")
    print("="*80)
    print(f"输出目录: {OUTPUT_DIR.absolute()}\n")
    
    reports = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        report = test_tts_asr_streaming(test_case, i)
        if report:
            reports.append(report)
    
    # 总结报告
    if reports:
        print("\n" + "="*80)
        print("📋 测试总结 (XTTS v2)")
        print("="*80)
        
        for report in reports:
            status = "✅" if report['similarity']['keyword_coverage'] >= 0.5 else "⚠️"
            print(f"\n{status} 测试 {report['test_id']} ({report['lang'].upper()}):")
            print(f"   音频文件: {report['audio_file']}")
            print(f"   总耗时: {report['total_time']:.2f}s")
            print(f"   关键词匹配: {report['similarity']['keyword_coverage']*100:.0f}%")
        
        # 计算平均性能
        avg_tts = sum(r['tts_time'] for r in reports) / len(reports)
        avg_asr = sum(r['asr_time'] for r in reports) / len(reports)
        avg_total = sum(r['total_time'] for r in reports) / len(reports)
        avg_coverage = sum(r['similarity']['keyword_coverage'] for r in reports) / len(reports)
        
        print(f"\n{'─'*80}")
        print("平均性能:")
        print(f"  TTS 生成: {avg_tts:.2f}s")
        print(f"  ASR 识别: {avg_asr:.2f}s")
        print(f"  总耗时: {avg_total:.2f}s")
        print(f"  关键词匹配率: {avg_coverage*100:.0f}%")
        print(f"{'─'*80}\n")
        
        print(f"✅ 所有音频文件已保存到: {OUTPUT_DIR.absolute()}")
        print("   请手动检查音频质量\n")
    else:
        print("\n❌ 所有测试失败\n")


if __name__ == '__main__':
    main()

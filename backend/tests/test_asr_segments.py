"""
ASR 分段分句功能测试
验证 Faster-Whisper 的自动分段能力
"""

import subprocess
import json
from pathlib import Path

# 配置
ASR_PYTHON = r"C:/Users/74090/Miniconda3/py313/envs/asr/python.exe"
ASR_SCRIPT = Path(__file__).parent / "scripts" / "faster_whisper_wrapper.py"
TEST_AUDIO = Path(__file__).parent.parent / "testresources" / "test_zero_shot.wav"

print("=" * 70)
print("ASR 分段分句功能测试")
print("=" * 70)

print(f"\n测试音频: {TEST_AUDIO.name}")
print(f"文件大小: {TEST_AUDIO.stat().st_size / 1024:.1f} KB\n")

# 调用 ASR
cmd = [
    str(ASR_PYTHON),
    str(ASR_SCRIPT),
    str(TEST_AUDIO),
    "--model", "small",
    "--compute-type", "int8",
    "--cpu-threads", "16"
]

print("执行 ASR...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

if result.returncode != 0:
    print(f"❌ 失败: {result.stderr}")
    exit(1)

# 解析结果
output = json.loads(result.stdout)

print("\n✅ ASR 转录成功\n")
print(f"完整文本: {output['text'][:100]}...\n")
print(f"音频时长: {output['duration']:.2f}s")
print(f"识别语言: {output['language']}")
print(f"RTF: {output['rtf']:.3f}x\n")

# 显示分段信息
segments = output.get('segments', [])
print(f"分段数量: {len(segments)}\n")
print("=" * 70)
print("分段详情:")
print("=" * 70)

for i, seg in enumerate(segments[:10], 1):  # 只显示前10段
    duration = seg['end'] - seg['start']
    print(f"\n[{i}] {seg['start']:.2f}s - {seg['end']:.2f}s (时长: {duration:.2f}s)")
    print(f"    {seg['text']}")

if len(segments) > 10:
    print(f"\n... 还有 {len(segments) - 10} 个分段未显示")

print("\n" + "=" * 70)
print("✅ 测试完成")
print(f"总分段数: {len(segments)}")

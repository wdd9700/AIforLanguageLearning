"""
流式传输测试 - 第1部分：TTS 流式音频生成
测试 TTS 生成的流式音频块
"""

import subprocess
import time
from pathlib import Path

# 配置
TTS_PYTHON = r"C:/Users/74090/Miniconda3/envs/torchnb311/python.exe"
TTS_SCRIPT = Path(__file__).parent.parent / "env_check" / "run_cosyvoice2_stream_multilang.py"

# 测试文本
TEST_TEXT = "你好，这是语音合成系统的流式传输测试。人工智能正在改变我们的生活方式。"

print("=" * 70)
print("TTS 流式音频生成测试")
print("=" * 70)
print(f"\n测试文本: {TEST_TEXT}\n")

# 准备输入
import json
input_data = {
    "text": TEST_TEXT,
    "speaker": "中文女",
    "streaming": True  # 流式模式
}

print(f"调用 TTS 脚本: {TTS_SCRIPT}")
print(f"Python: {TTS_PYTHON}\n")

start_time = time.time()

# 运行 TTS（通过 stdin 传递 JSON）
proc = subprocess.Popen(
    [str(TTS_PYTHON), str(TTS_SCRIPT)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 发送输入
input_json = json.dumps(input_data, ensure_ascii=False)
stdout, stderr = proc.communicate(input=input_json, timeout=60)

elapsed = time.time() - start_time

print(f"执行完成 (耗时: {elapsed:.2f}s)\n")

# 显示输出
print("STDERR 输出:")
print("-" * 70)
for line in stderr.split('\n')[-30:]:  # 只显示最后30行
    if line.strip():
        print(line)

print("\n" + "=" * 70)
print("✅ TTS 流式测试完成")
print(f"总耗时: {elapsed:.2f}s")

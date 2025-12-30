"""生成简单的参考音频（prompt wav）。

用于 XTTS v2 等支持“参考音频/说话人克隆”的 TTS 场景。

说明：这里生成的是“占位用”的合成音（非真实人声），主要用于打通链路。
"""
import numpy as np
import scipy.io.wavfile as wavfile
import os

# 生成简单的正弦波作为参考音频（粗略模拟人声频率范围）
# 采样率保持常见值，便于各类 TTS/ASR 工具读取。
sample_rate = 16000
duration = 2.0  # 2 秒

# 生成混合频率（模拟人声）
t = np.linspace(0, duration, int(sample_rate * duration))
# 基频 + 谐波
frequencies = [200, 400, 600, 800]  # Hz
audio = np.zeros_like(t)
for freq in frequencies:
    audio += np.sin(2 * np.pi * freq * t) / len(frequencies)

# 添加包络（避免突然开始/结束）
envelope = np.concatenate([
    np.linspace(0, 1, int(sample_rate * 0.1)),  # 淡入
    np.ones(int(sample_rate * (duration - 0.2))),  # 稳定
    np.linspace(1, 0, int(sample_rate * 0.1))   # 淡出
])
audio = audio * envelope

# 归一化到 int16 范围
audio = (audio * 32767).astype(np.int16)

# 保存
output_path = r'E:\projects\AiforForiegnLanguageLearning\backend\assets\reference_voice.wav'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
wavfile.write(output_path, sample_rate, audio)

print(f"Reference audio saved to: {output_path}")
print(f"Sample rate: {sample_rate} Hz")
print(f"Duration: {duration} seconds")

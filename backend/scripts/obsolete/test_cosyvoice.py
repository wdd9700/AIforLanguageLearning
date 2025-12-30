"""测试 CosyVoice2 零样本功能"""
import sys
import os
sys.path.insert(0, r'E:\models\CosyVoice\CosyVoice')
sys.path.insert(0, r'E:\models\CosyVoice\CosyVoice\third_party\Matcha-TTS')
os.chdir(r'E:\models\CosyVoice\CosyVoice')

from cosyvoice.cli.cosyvoice import CosyVoice2
import torchaudio

# 加载模型（强制使用 CPU，避免 RTX 5080 CUDA 兼容性问题）
print("Loading CosyVoice2-0.5B model (CPU mode)...")
import torch
torch.cuda.is_available = lambda: False  # 强制 CPU 模式
model = CosyVoice2(r'E:\models\CosyVoice\CosyVoice\pretrained_models\CosyVoice2-0.5B', 
                   load_jit=False, load_trt=False, fp16=False)  # CPU 模式不用 FP16
print("Model loaded!")

# 加载参考音频（使用 scipy 避免 FFmpeg 依赖）
reference_audio_path = r'E:\projects\AiforForiegnLanguageLearning\backend\assets\reference_voice.wav'
print(f"\nLoading reference audio from: {reference_audio_path}")

# 使用 scipy 直接读取 WAV 文件
import scipy.io.wavfile as wavfile
import numpy as np
import torch

sample_rate, audio_data = wavfile.read(reference_audio_path)
print(f"Loaded audio: shape={audio_data.shape}, sample_rate={sample_rate}")

# 转换为 torch tensor 并归一化到 [-1, 1]
audio_float = audio_data.astype(np.float32) / 32768.0
waveform = torch.from_numpy(audio_float).unsqueeze(0)  # 添加 batch 维度

# 重采样到 16kHz（如果需要）
if sample_rate != 16000:
    print(f"Resampling from {sample_rate}Hz to 16000Hz...")
    import torchaudio
    resampler = torchaudio.transforms.Resample(sample_rate, 16000)
    waveform = resampler(waveform)

prompt_speech_16k = waveform
print(f"Reference audio ready, shape: {prompt_speech_16k.shape}")

# 测试零样本合成
test_text = "Hello world, this is a test of CosyVoice2 zero-shot text to speech synthesis."
print(f"\nSynthesizing: {test_text}")

try:
    for i, result in enumerate(model.inference_zero_shot(
        test_text,
        "",  # prompt_text 为空
        prompt_speech_16k,
        stream=False
    )):
        print(f"\nSynthesis successful!")
        print(f"Audio shape: {result['tts_speech'].shape}")
        print(f"Sample rate: {model.sample_rate}")
        
        # 保存音频（使用 scipy 避免 FFmpeg 依赖）
        output_path = r'E:\projects\AiforForiegnLanguageLearning\backend\temp\test_zero_shot.wav'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 转换为 numpy 并保存
        audio_numpy = result['tts_speech'].cpu().numpy().squeeze()
        audio_int16 = (audio_numpy * 32767).astype(np.int16)
        wavfile.write(output_path, model.sample_rate, audio_int16)
        
        print(f"Saved to: {output_path}")
        break  # 只取第一个结果
        
    print("\n✅ Test completed successfully!")
    
except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()


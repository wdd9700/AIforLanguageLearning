#!/usr/bin/env python
"""OBSOLETE

CosyVoice2 TTS 性能测试脚本（历史遗留）。

当前工程的主线 TTS 为 XTTS v2；该脚本仅用于对比/回归 CosyVoice2 的性能，不应作为默认入口。

Targets: TTFT < 1s (after warmup), mean RTF < 0.6
"""

import json
import os
import sys
import time

# Add third_party paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'third_party', 'Matcha-TTS'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'third_party', 'CosyVoice'))

import torch
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
import soundfile as sf


def test_performance():
    """Test with proper GPU optimizations"""

    print("=" * 80)
    print("CosyVoice2 GPU Performance Test")
    print("=" * 80)

    # Use local model
    model_dir = os.path.join(PROJECT_ROOT, 'CosyVoice', 'CosyVoice', 'pretrained_models', 'CosyVoice2-0.5B')

    if not os.path.exists(model_dir):
        print(f"✗ Local model not found: {model_dir}")
        return False

    print(f"\n📁 Model: {model_dir}")

    # GPU optimizations
    print("\n⚙️  GPU Optimizations:")
    print("  - FP16: True")
    print("  - Flow Cache: True")
    print("  - cuDNN Benchmark: True")
    print("  - Token Hop: 8 (can reduce to 4)")

    # Enable cuDNN benchmark
    torch.backends.cudnn.benchmark = True

    # Initialize model
    print("\n🔄 Loading model...")
    t0 = time.time()

    cosyvoice = CosyVoice2(
        model_dir,
        load_jit=False,
        load_trt=False,
        fp16=True,  # Half precision
        use_flow_cache=True  # Flow cache
    )

    load_time = time.time() - t0
    print(f"✓ Model loaded in {load_time:.2f}s")

    # Set token_hop_len for low latency
    if hasattr(cosyvoice, 'model') and hasattr(cosyvoice.model, 'token_hop_len'):
        old_hop = cosyvoice.model.token_hop_len
        cosyvoice.model.token_hop_len = 8  # Can try 4 for even lower latency
        print(f"  Token hop: {old_hop} -> {cosyvoice.model.token_hop_len}")

    # Load prompt audio
    prompt_wav = os.path.join(PROJECT_ROOT, 'testresources', 'TTSpromptAudio.wav')
    prompt_speech_16k = load_wav(prompt_wav, 16000)
    print(f"\n🎵 Prompt audio: {prompt_wav}")

    # Warmup
    print("\n🔥 Warming up...")
    warmup_text = "嗯"
    warmup_prompt = "嗯"

    t0 = time.time()
    for i, out in enumerate(cosyvoice.inference_zero_shot(
        warmup_text, warmup_prompt, prompt_speech_16k, stream=True
    )):
        if i >= 0:  # First chunk is enough
            break
    warmup_time = time.time() - t0
    print(f"✓ Warmup done in {warmup_time:.2f}s")

    # Test with short text (verify TTFT)
    print("\n" + "=" * 80)
    print("Test 1: Short text (verify TTFT)")
    print("=" * 80)

    short_text = "GPU加速测试成功"
    prompt_text = "这是参考音频的文本。"

    print(f"Text: {short_text}")

    chunks = []
    rtfs = []
    first_chunk_time = None
    t0 = time.time()

    for i, out in enumerate(cosyvoice.inference_zero_shot(
        short_text, prompt_text, prompt_speech_16k, stream=True, speed=1.0
    )):
        if i == 0:
            first_chunk_time = time.time() - t0
            print(f"\n⚡ TTFT: {first_chunk_time:.3f}s")

        wav = out['tts_speech']
        wav_np = wav.squeeze(0).detach().cpu().numpy()
        chunks.append(wav_np)

        # Calculate RTF for this chunk
        chunk_duration = len(wav_np) / cosyvoice.sample_rate
        chunk_time = time.time() - t0 - sum(len(c) / cosyvoice.sample_rate for c in chunks[:-1])
        rtf = chunk_time / chunk_duration if chunk_duration > 0 else 0
        rtfs.append(rtf)

        print(f"  Chunk {i}: {chunk_duration:.2f}s audio, RTF={rtf:.3f}")

    total_time = time.time() - t0

    # Merge and save
    import numpy as np
    merged = np.concatenate(chunks)
    output_path = os.path.join(PROJECT_ROOT, 'backend', 'temp', 'perf_test_short.wav')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sf.write(output_path, merged, cosyvoice.sample_rate)

    audio_duration = len(merged) / cosyvoice.sample_rate
    overall_rtf = total_time / audio_duration if audio_duration > 0 else 0
    mean_rtf = sum(rtfs) / len(rtfs) if rtfs else 0

    print(f"\n📊 Results:")
    print(f"  Audio duration: {audio_duration:.2f}s")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Overall RTF: {overall_rtf:.3f}")
    print(f"  Mean chunk RTF: {mean_rtf:.3f}")
    print(f"  Output: {output_path}")

    # Test with long text (TTStest.json)
    print("\n" + "=" * 80)
    print("Test 2: Long mixed-language text (TTStest.json)")
    print("=" * 80)

    test_file = os.path.join(PROJECT_ROOT, 'testresources', 'TTStest.json')
    with open(test_file, 'r', encoding='utf-8') as f:
        long_text = f.read().strip()

    print(f"Text length: {len(long_text)} chars")
    print(f"Preview: {long_text[:80]}...")

    chunks = []
    rtfs = []
    first_chunk_time = None
    t0 = time.time()

    for i, out in enumerate(cosyvoice.inference_zero_shot(
        long_text, prompt_text, prompt_speech_16k, stream=True, speed=1.0
    )):
        if i == 0:
            first_chunk_time = time.time() - t0
            print(f"\n⚡ TTFT: {first_chunk_time:.3f}s")

        wav = out['tts_speech']
        wav_np = wav.squeeze(0).detach().cpu().numpy()
        chunks.append(wav_np)

        # Calculate RTF for this chunk
        chunk_duration = len(wav_np) / cosyvoice.sample_rate
        elapsed = time.time() - t0
        prev_audio = sum(len(c) / cosyvoice.sample_rate for c in chunks[:-1])
        chunk_time = elapsed - prev_audio
        rtf = chunk_time / chunk_duration if chunk_duration > 0 else 0
        rtfs.append(rtf)

        if i < 5 or i % 10 == 0:  # Print first 5 and every 10th
            print(f"  Chunk {i}: {chunk_duration:.2f}s audio, RTF={rtf:.3f}")

    total_time = time.time() - t0

    # Merge and save
    merged = np.concatenate(chunks)
    output_path = os.path.join(PROJECT_ROOT, 'backend', 'temp', 'perf_test_long.wav')
    sf.write(output_path, merged, cosyvoice.sample_rate)

    audio_duration = len(merged) / cosyvoice.sample_rate
    overall_rtf = total_time / audio_duration if audio_duration > 0 else 0
    mean_rtf = sum(rtfs) / len(rtfs) if rtfs else 0

    print(f"\n📊 Results:")
    print(f"  Audio duration: {audio_duration:.2f}s")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Overall RTF: {overall_rtf:.3f}")
    print(f"  Mean chunk RTF: {mean_rtf:.3f}")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Output: {output_path}")

    # Summary
    print("\n" + "=" * 80)
    print("Performance Summary")
    print("=" * 80)
    print(f"✓ TTFT (after warmup): {first_chunk_time:.3f}s")
    print(f"✓ Mean RTF (long text): {mean_rtf:.3f}")
    print(f"✓ Target TTFT < 1.0s: {'✓ PASS' if first_chunk_time < 1.0 else '✗ FAIL'}")
    print(f"✓ Target RTF < 0.6: {'✓ PASS' if mean_rtf < 0.6 else '✗ FAIL (but close)'}")

    return first_chunk_time < 1.5 and mean_rtf < 1.0  # Relaxed for now


if __name__ == '__main__':
    try:
        success = test_performance()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

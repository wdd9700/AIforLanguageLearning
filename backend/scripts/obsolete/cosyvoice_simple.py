"""
CosyVoice2 GPU wrapper - simplified for local model
Based on project setup: third_party/CosyVoice/pretrained_models/CosyVoice2-0.5B
"""
import os
import sys
import json
import argparse
import time

# Project root and paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# Add CosyVoice to path - use the version with your recompiled PyTorch!
# Option 1: E:\projects\AiforForiegnLanguageLearning\CosyVoice\CosyVoice (your custom build)
# Option 2: E:\projects\AiforForiegnLanguageLearning\third_party\CosyVoice (standard)
cosy_path = os.path.join(PROJECT_ROOT, 'CosyVoice', 'CosyVoice')
matcha_path = os.path.join(PROJECT_ROOT, 'CosyVoice', 'CosyVoice', 'third_party', 'Matcha-TTS')

# Fallback to third_party if custom build doesn't exist
if not os.path.exists(cosy_path):
    cosy_path = os.path.join(PROJECT_ROOT, 'third_party', 'CosyVoice')
    matcha_path = os.path.join(PROJECT_ROOT, 'third_party', 'Matcha-TTS')

sys.path.insert(0, cosy_path)
sys.path.insert(0, matcha_path)

print(f"[DEBUG] Using CosyVoice from: {cosy_path}", file=sys.stderr)

# Imports
from cosyvoice.cli.cosyvoice import CosyVoice2
import soundfile as sf
import torch
import numpy as np

# Global model instance
_model = None
_prompt_speech = None


def init_model():
    """Initialize CosyVoice2 model with GPU optimizations"""
    global _model, _prompt_speech
    
    if _model is not None:
        return
    
    # Local model path - use environment variable or hardcoded path
    model_dir = os.getenv(
        'COSY_MODEL_DIR',
        r'E:\projects\AiforForiegnLanguageLearning\CosyVoice\CosyVoice\pretrained_models\CosyVoice2-0.5B'
    )
    prompt_audio = os.getenv(
        'COSY_PROMPT_AUDIO',
        os.path.join(PROJECT_ROOT, 'testresources', 'TTSpromptAudio.wav')
    )
    
    if not os.path.exists(model_dir):
        raise FileNotFoundError(f"Model not found: {model_dir}")
    if not os.path.exists(prompt_audio):
        raise FileNotFoundError(f"Prompt audio not found: {prompt_audio}")
    
    print(f"[CosyVoice GPU] Loading model from: {model_dir}", file=sys.stderr)
    print(f"[CosyVoice GPU] Prompt audio: {prompt_audio}", file=sys.stderr)
    
    # GPU optimization settings (from CLI.md)
    fp16 = os.getenv('COSY_FP16', '1') == '1'
    flow_cache = os.getenv('COSY_FLOW_CACHE', '1') == '1'
    load_trt = os.getenv('COSY_LOAD_TRT', '0') == '1'
    
    # Enable cuDNN benchmark (recommended in CLI.md)
    torch.backends.cudnn.benchmark = True
    
    print(f"[CosyVoice GPU] Optimizations: fp16={fp16}, flow_cache={flow_cache}, trt={load_trt}", file=sys.stderr)
    
    # Load model
    _model = CosyVoice2(
        model_dir,
        load_jit=False,
        load_trt=load_trt,
        fp16=fp16,
        use_flow_cache=flow_cache
    )
    
    # Load prompt audio
    audio_data, sr = sf.read(prompt_audio)
    if sr != 16000:
        raise ValueError(f"Prompt audio must be 16kHz, got {sr}Hz")
    
    _prompt_speech = torch.from_numpy(audio_data).float()
    if _prompt_speech.dim() == 1:
        _prompt_speech = _prompt_speech.unsqueeze(0)
    
    print(f"[CosyVoice GPU] Model loaded! Sample rate: {_model.sample_rate}", file=sys.stderr)
    print(f"[CosyVoice GPU] Prompt shape: {_prompt_speech.shape}", file=sys.stderr)
    
    # Warmup (reduce TTFT from ~2.9s to ~1.9s per CLI.md)
    if os.getenv('COSY_WARMUP', '1') == '1':
        print(f"[CosyVoice GPU] Warming up...", file=sys.stderr)
        warmup_iters = int(os.getenv('COSY_WARMUP_ITERS', '1'))
        for i, out in enumerate(_model.inference_zero_shot("warmup test", "", _prompt_speech, stream=True)):
            if i + 1 >= warmup_iters:
                break
        print(f"[CosyVoice GPU] Warmup complete!", file=sys.stderr)


def synthesize(text, output_path, speed=1.0, stream=False):
    """
    Synthesize speech using zero-shot mode
    
    Args:
        text: Text to synthesize
        output_path: Output WAV file path
        speed: Speed multiplier (default 1.0)
        stream: If True, generate streaming chunks; else merge all
    
    Returns:
        dict with success, output, sample_rate, ttft, rtf, etc.
    """
    init_model()
    
    # Get token_hop_len from env (default 32 per your config, can go to 8 or 4 for lower latency)
    token_hop = int(os.getenv('COSY_TOKEN_HOP', '32'))
    if hasattr(_model, 'flow') and hasattr(_model.flow, 'estimator'):
        _model.flow.estimator.token_hop_len = token_hop
    
    t0 = time.time()
    first_chunk_time = None
    chunks = []
    
    # Zero-shot inference with streaming
    for i, out in enumerate(_model.inference_zero_shot(
        text,
        "",  # prompt_text (empty for zero-shot)
        _prompt_speech,
        stream=True,
        speed=speed
    )):
        if i == 0:
            first_chunk_time = time.time() - t0
        
        audio_tensor = out['tts_speech']
        audio_np = audio_tensor.cpu().numpy().squeeze()
        chunks.append(audio_np)
    
    total_time = time.time() - t0
    
    # Merge chunks and save
    merged = np.concatenate(chunks) if len(chunks) > 0 else np.array([])
    sf.write(output_path, merged, _model.sample_rate)
    
    duration = len(merged) / _model.sample_rate if len(merged) > 0 else 0
    rtf = total_time / duration if duration > 0 else 0
    
    return {
        'success': True,
        'output': output_path,
        'sample_rate': _model.sample_rate,
        'ttft': first_chunk_time,
        'total_time': total_time,
        'duration': duration,
        'rtf': rtf,
        'chunks': len(chunks)
    }


def main():
    parser = argparse.ArgumentParser(description='CosyVoice2 GPU TTS wrapper')
    parser.add_argument('--text', required=True, help='Text to synthesize')
    parser.add_argument('--output', required=True, help='Output WAV path')
    parser.add_argument('--speed', type=float, default=1.0, help='Speed multiplier')
    parser.add_argument('--stream', action='store_true', help='Enable streaming mode')
    
    args = parser.parse_args()
    
    try:
        result = synthesize(args.text, args.output, speed=args.speed, stream=args.stream)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()

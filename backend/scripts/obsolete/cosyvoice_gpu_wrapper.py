"""
CosyVoice2 GPU TTS Wrapper for Backend Integration
Based on env_check/run_cosyvoice2_zero_shot.py
Optimized for RTX 5080 with recompiled PyTorch
"""
import os
import sys
import json
import argparse
import time

# Add project paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# Use third_party/CosyVoice (standard location per project structure)
cosy_path = os.path.join(PROJECT_ROOT, 'third_party', 'CosyVoice')
matcha_path = os.path.join(PROJECT_ROOT, 'third_party', 'Matcha-TTS')
sys.path.insert(0, cosy_path)
sys.path.insert(0, matcha_path)

# HF hub compatibility shim (from project script)
try:
    import huggingface_hub as hfh
    if not hasattr(hfh, 'cached_download'):
        from huggingface_hub import hf_hub_download
        
        def cached_download(repo_id, filename, cache_dir=None, force_filename=None,
                           force_download=False, proxies=None, etag_timeout=10,
                           resume_download=False, local_files_only=False,
                           use_auth_token=None, revision=None, subfolder=None, **kwargs):
            return hf_hub_download(
                repo_id, filename, subfolder=subfolder, revision=revision,
                cache_dir=cache_dir, local_files_only=local_files_only,
                force_download=force_download, proxies=proxies,
                etag_timeout=etag_timeout, resume_download=resume_download,
                token=use_auth_token, force_filename=force_filename
            )
        setattr(hfh, 'cached_download', cached_download)
        print("huggingface_hub.cached_download shimmed via hf_hub_download", file=sys.stderr)
except Exception as e:
    print(f"HF hub shim failed: {e}", file=sys.stderr)

import torch
from cosyvoice.cli.cosyvoice import CosyVoice2
import soundfile as sf

# Global model instance
_model = None
_prompt_speech_16k = None


def get_model(use_fp16=True, use_flow_cache=True, load_trt=False):
    """Initialize CosyVoice2 with GPU optimizations"""
    global _model, _prompt_speech_16k
    
    if _model is not None:
        return _model
    
    # Use local model if available, otherwise download from ModelScope
    local_model_path = os.path.join(PROJECT_ROOT, 'CosyVoice', 'CosyVoice', 'pretrained_models', 'CosyVoice2-0.5B')
    if os.path.exists(local_model_path):
        model_id = local_model_path
        print(f"[CosyVoice GPU] Using local model: {model_id}", file=sys.stderr)
    else:
        model_id = os.getenv('COSY_MODEL_ID', 'iic/CosyVoice2-0.5B')
        print(f"[CosyVoice GPU] Downloading model: {model_id}", file=sys.stderr)
    
    # Prompt audio path
    prompt_wav = os.getenv(
        'COSY_PROMPT_AUDIO',
        os.path.join(PROJECT_ROOT, 'testresources', 'TTSpromptAudio.wav')
    )
    
    print(f"[CosyVoice GPU] Prompt audio: {prompt_wav}", file=sys.stderr)
    
    # Load TRT from env if not specified
    if load_trt is False and os.getenv("COSY_LOAD_TRT", "0") == "1":
        load_trt = True
    
    # Initialize model with GPU optimizations
    _model = CosyVoice2(
        model_id,
        load_jit=False,
        load_trt=load_trt,
        fp16=use_fp16,
        use_flow_cache=use_flow_cache
    )
    
    # Enable cuDNN benchmark (vocoder optimization)
    if os.getenv("COSY_DISABLE_CUDNN", "0") != "1":
        torch.backends.cudnn.benchmark = True
    
    # Tune streaming hop size for lower latency
    token_hop = int(os.getenv('COSY_TOKEN_HOP', '8'))
    if hasattr(_model, 'model') and hasattr(_model.model, 'token_hop_len'):
        old_hop = _model.model.token_hop_len
        _model.model.token_hop_len = token_hop
        print(f"[CosyVoice2] token_hop_len: {old_hop} -> {token_hop}", file=sys.stderr)
    
    # Load prompt audio (must be 16kHz mono)
    prompt_speech, sr = sf.read(prompt_wav)
    if sr != 16000:
        raise ValueError(f"Prompt audio must be 16kHz, got {sr}Hz")
    
    # Convert to mono if stereo
    if len(prompt_speech.shape) > 1:
        prompt_speech = prompt_speech.mean(axis=1)
    
    _prompt_speech_16k = torch.from_numpy(prompt_speech).float()
    if _prompt_speech_16k.dim() == 1:
        _prompt_speech_16k = _prompt_speech_16k.unsqueeze(0)  # [T] -> [1, T]
    
    print(f"[CosyVoice GPU] Model loaded! Sample rate: {_model.sample_rate}", file=sys.stderr)
    
    # Warmup to reduce TTFT (2.9s -> 1.9s)
    if os.getenv("COSY_WARMUP", "1") == "1":
        print(f"[CosyVoice GPU] Warming up...", file=sys.stderr)
        try:
            warmup_iters = int(os.getenv("COSY_WARMUP_ITERS", "1"))
            for i, out in enumerate(_model.inference_zero_shot("嗯。", "参考音频文本。", _prompt_speech_16k, stream=True)):
                if i + 1 >= warmup_iters:
                    break
            print(f"Warmup done (COSY_WARMUP=1).", file=sys.stderr)
        except Exception as e:
            print(f"Warmup failed: {e}", file=sys.stderr)
    
    return _model


def synthesize(text, output_path, prompt_text=None, speed=1.0):
    """
    Synthesize speech using zero-shot mode
    
    Args:
        text: Text to synthesize
        output_path: Output audio file path
        prompt_text: Text for the reference audio (defaults to generic Chinese text)
        speed: Speech speed multiplier
    
    Returns:
        dict with success, output, sample_rate, ttft, rtf, duration
    """
    # Use a generic prompt text if not provided
    if prompt_text is None or prompt_text.strip() == "":
        prompt_text = "这是参考音频的文本。"
    
    model = get_model(
        use_fp16=os.getenv('COSY_FP16', '1') == '1',
        use_flow_cache=os.getenv('COSY_FLOW_CACHE', '1') == '1',
        load_trt=os.getenv('COSY_LOAD_TRT', '0') == '1'
    )
    
    t0 = time.time()
    first_chunk_time = None
    chunks = []
    
    # Streaming zero-shot inference
    for i, out in enumerate(model.inference_zero_shot(
        text, prompt_text, _prompt_speech_16k, stream=True, speed=speed
    )):
        if i == 0:
            first_chunk_time = time.time() - t0
        
        wav = out['tts_speech']
        wav_np = wav.squeeze(0).detach().cpu().numpy()
        chunks.append(wav_np)
    
    total_time = time.time() - t0
    
    # Concatenate chunks and save
    import numpy as np
    merged = np.concatenate(chunks) if len(chunks) > 0 else np.array([])
    sf.write(output_path, merged, model.sample_rate)
    
    duration = len(merged) / model.sample_rate if len(merged) > 0 else 0
    rtf = total_time / duration if duration > 0 else 0
    
    return {
        'success': True,
        'output': output_path,
        'sample_rate': model.sample_rate,
        'ttft': first_chunk_time,
        'total_time': total_time,
        'duration': duration,
        'rtf': rtf,
        'chunks': len(chunks)
    }


def main():
    parser = argparse.ArgumentParser(description='CosyVoice2 GPU TTS Wrapper')
    parser.add_argument('--text', required=True, help='Text to synthesize')
    parser.add_argument('--output', required=True, help='Output WAV path')
    parser.add_argument('--prompt_text', default='', help='Prompt text for zero-shot')
    parser.add_argument('--speed', type=float, default=1.0, help='Speed multiplier')
    
    args = parser.parse_args()
    
    try:
        result = synthesize(args.text, args.output, args.prompt_text, args.speed)
        print(json.dumps(result))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }), file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

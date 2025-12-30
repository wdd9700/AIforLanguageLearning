"""
CosyVoice2 GPU-accelerated streaming TTS wrapper for Node.js integration
Based on project's optimized env_check/run_cosyvoice2_zero_shot.py
Supports: FP16, TensorRT, flow cache, streaming output
"""
import os
import sys
import json
import argparse
import time

# Ensure local CosyVoice and Matcha-TTS are importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
cosy_path = os.path.join(ROOT, 'third_party', 'CosyVoice')
matcha_path = os.path.join(ROOT, 'third_party', 'Matcha-TTS')
if cosy_path not in sys.path:
    sys.path.insert(0, cosy_path)
if matcha_path not in sys.path:
    sys.path.insert(0, matcha_path)

# HF hub compatibility shim
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
except Exception as e:
    print(f'HF hub compat shim failed: {e}', file=sys.stderr)

from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
import soundfile as sf
import torch


# Global model instance (persistent for fast reuse)
_model = None
_prompt_speech_16k = None


def get_model(use_fp16=True, use_flow_cache=True, load_trt=False):
    """
    Initialize CosyVoice2 with GPU optimization:
    - FP16 for memory/speed (or BF16 via AMP)
    - Flow cache for lower latency
    - Optional TensorRT for flow estimator
    """
    global _model, _prompt_speech_16k
    
    if _model is None:
        model_id = 'iic/CosyVoice2-0.5B'
        
        # Load TRT from env if not specified
        if load_trt is None:
            env_trt = os.getenv("COSY_LOAD_TRT", "0")
            load_trt = env_trt.strip() in ("1", "true", "True", "yes", "on")
        
        _model = CosyVoice2(
            model_id,
            load_jit=False,
            load_trt=load_trt,
            fp16=use_fp16,
            use_flow_cache=use_flow_cache
        )
        
        # Enable cuDNN benchmark for faster convolutions (vocoder)
        if os.getenv("COSY_DISABLE_CUDNN", "0") != "1":
            torch.backends.cudnn.benchmark = True
        
        # Optimize streaming hop size (smaller = lower TTFT)
        if hasattr(_model, 'model') and hasattr(_model.model, 'token_hop_len'):
            hop_env = os.getenv('COSY_TOKEN_HOP', '32')  # Default 32 for best RTF
            _model.model.token_hop_len = int(hop_env)
        
        # Load reference audio (project's default prompt)
        prompt_path = os.getenv('COSY_PROMPT_WAV')
        if not prompt_path:
            prompt_path = os.path.join(ROOT, 'testresources', 'TTSpromptAudio.wav')
        
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Reference audio not found: {prompt_path}")
        
        _prompt_speech_16k = load_wav(prompt_path, 16000)
        
        # Warmup to compile CUDA kernels (reduce first-call latency)
        if os.getenv("COSY_WARMUP", "1") == "1":
            try:
                warmup_iters = int(os.getenv("COSY_WARMUP_ITERS", "1"))
                for i, out in enumerate(_model.inference_zero_shot(
                    "warmup", "", _prompt_speech_16k, stream=True
                )):
                    _ = out.get('tts_speech', None)
                    if i + 1 >= warmup_iters:
                        break
            except Exception as e:
                print(f"Warmup failed: {e}", file=sys.stderr)
    
    return _model


def synthesize(text, output_path, prompt_text="", speed=1.0, stream=False):
    """
    Synthesize speech using CosyVoice2 zero-shot mode
    
    Args:
        text: Text to synthesize
        output_path: Output WAV path
        prompt_text: Optional prompt text (can be empty for zero-shot)
        speed: Speech speed multiplier
        stream: If True, return streaming chunks; if False, merge all chunks
    
    Returns:
        dict with success, output, sample_rate, chunks (if stream=True)
    """
    model = get_model()
    
    t0 = time.time()
    first_chunk_time = None
    chunks = []
    
    for i, out in enumerate(model.inference_zero_shot(
        text, prompt_text, _prompt_speech_16k, stream=True, speed=speed
    )):
        if i == 0:
            first_chunk_time = time.time() - t0
        
        audio_tensor = out['tts_speech']
        audio_np = audio_tensor.cpu().numpy().squeeze()
        
        if stream:
            # For streaming: return each chunk separately
            chunk_path = output_path.replace('.wav', f'_chunk{i}.wav')
            sf.write(chunk_path, audio_np, model.sample_rate)
            chunks.append({
                'index': i,
                'path': chunk_path,
                'duration': len(audio_np) / model.sample_rate
            })
        else:
            # For non-streaming: accumulate chunks
            chunks.append(audio_np)
    
    total_time = time.time() - t0
    
    if not stream:
        # Merge all chunks into single file
        import numpy as np
        merged = np.concatenate(chunks)
        sf.write(output_path, merged, model.sample_rate)
        
        return {
            'success': True,
            'output': output_path,
            'sample_rate': model.sample_rate,
            'ttft': first_chunk_time,
            'total_time': total_time,
            'duration': len(merged) / model.sample_rate,
            'rtf': total_time / (len(merged) / model.sample_rate) if len(merged) > 0 else 0
        }
    else:
        return {
            'success': True,
            'output': output_path,
            'sample_rate': model.sample_rate,
            'chunks': chunks,
            'ttft': first_chunk_time,
            'total_time': total_time
        }


def main():
    parser = argparse.ArgumentParser(description='CosyVoice2 GPU TTS Wrapper')
    parser.add_argument('--text', required=True, help='Text to synthesize')
    parser.add_argument('--output', required=True, help='Output WAV path')
    parser.add_argument('--prompt_text', default='', help='Prompt text for zero-shot')
    parser.add_argument('--speed', type=float, default=1.0, help='Speed multiplier')
    parser.add_argument('--stream', action='store_true', help='Enable streaming output')
    parser.add_argument('--fp16', type=int, default=1, help='Use FP16 (1) or FP32 (0)')
    parser.add_argument('--flow_cache', type=int, default=1, help='Use flow cache')
    parser.add_argument('--load_trt', type=int, default=None, help='Load TensorRT estimator')
    
    args = parser.parse_args()
    
    try:
        # Override model config from args
        global _model
        if _model is None:
            get_model(
                use_fp16=bool(args.fp16),
                use_flow_cache=bool(args.flow_cache),
                load_trt=bool(args.load_trt) if args.load_trt is not None else None
            )
        
        result = synthesize(
            text=args.text,
            output_path=args.output,
            prompt_text=args.prompt_text,
            speed=args.speed,
            stream=args.stream
        )
        
        # Output JSON for Node.js parsing
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'type': type(e).__name__
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == '__main__':
    main()

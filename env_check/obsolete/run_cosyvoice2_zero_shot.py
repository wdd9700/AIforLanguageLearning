import os
import sys
import argparse

# Optional switch: set COSY_FORCE_CPU=1 to force CPU inference
if os.getenv("COSY_FORCE_CPU", "0") == "1":
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

# Ensure local CosyVoice and Matcha-TTS are importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
cosy_path = os.path.join(ROOT, 'third_party', 'CosyVoice')
matcha_path = os.path.join(ROOT, 'third_party', 'Matcha-TTS')
if cosy_path not in sys.path:
    sys.path.insert(0, cosy_path)
if matcha_path not in sys.path:
    sys.path.insert(0, matcha_path)

# HF hub compatibility shim: provide huggingface_hub.cached_download via hf_hub_download if missing
try:
    import huggingface_hub as hfh  # type: ignore
    if not hasattr(hfh, 'cached_download'):
        from huggingface_hub import hf_hub_download  # type: ignore

        def cached_download(
            repo_id,
            filename,
            cache_dir=None,
            force_filename=None,
            force_download=False,
            proxies=None,
            etag_timeout=10,
            resume_download=False,
            local_files_only=False,
            use_auth_token=None,
            revision=None,
            subfolder=None,
            mirror=None,
            **kwargs,
        ):
            # Map deprecated cached_download API to hf_hub_download
            return hf_hub_download(
                repo_id,
                filename,
                subfolder=subfolder,
                revision=revision,
                cache_dir=cache_dir,
                local_files_only=local_files_only,
                force_download=force_download,
                proxies=proxies,
                etag_timeout=etag_timeout,
                resume_download=resume_download,
                token=use_auth_token,
                force_filename=force_filename,
            )

        setattr(hfh, 'cached_download', cached_download)
        print('huggingface_hub.cached_download shimmed via hf_hub_download')
except Exception as e:
    print(f'HF hub compat shim failed: {e}')

from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
import soundfile as sf
import torch


def parse_args():
    p = argparse.ArgumentParser(description="Run CosyVoice2 zero-shot TTS (streaming) and save chunked wavs")
    p.add_argument("--text", type=str, default='收到好友从远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐，笑容如花儿般绽放。', help="Target text to synthesize")
    p.add_argument("--prompt_text", type=str, default='希望你以后能够做的比我还好呦。', help="Prompt text for zero-shot")
    p.add_argument("--prompt_wav", type=str, default=os.path.join(os.path.dirname(__file__), 'zero_shot_prompt.wav'), help="Path to 16kHz prompt wav")
    p.add_argument("--use_fp16", type=int, default=1, help="Use fp16 for model where supported (1/0)")
    p.add_argument("--use_flow_cache", type=int, default=1, help="Use flow cache variant if available (1/0)")
    p.add_argument("--speed", type=float, default=1.0, help="Synthesis speed multiplier")
    p.add_argument("--load_trt", type=int, default=None, help="Enable TensorRT backend if available (1/0). If omitted, read from env COSY_LOAD_TRT (default 0)")
    return p.parse_args()


def main():
    args = parse_args()

    # Model identifier from ModelScope; will auto-download to a cache dir on first run
    model_id = 'iic/CosyVoice2-0.5B'

    # Determine TRT flag from CLI or env
    env_trt = os.getenv("COSY_LOAD_TRT")
    load_trt = False
    if args.load_trt is not None:
        load_trt = bool(args.load_trt)
    elif env_trt is not None:
        load_trt = env_trt.strip() in ("1", "true", "True", "yes", "on")

    # Build synthesizer with requested precision/cache settings
    cosyvoice = CosyVoice2(model_id, load_jit=False, load_trt=load_trt, fp16=bool(args.use_fp16), use_flow_cache=bool(args.use_flow_cache))

    # Backend knobs: allow disabling cuDNN globally to avoid engine find failures on new architectures
    try:
        if os.getenv("COSY_DISABLE_CUDNN", "0") == "1":
            torch.backends.cudnn.enabled = False
            torch.backends.cudnn.benchmark = False
            print("[CosyVoice2] cuDNN disabled via COSY_DISABLE_CUDNN=1 (using ATen CUDA kernels)")
        else:
            # Enable cuDNN autotune for potentially faster convs (e.g., vocoder)
            torch.backends.cudnn.benchmark = True
    except Exception:
        pass

    # Tune streaming hop size for faster first-chunk latency (smaller -> lower latency, may trade slight quality)
    try:
        if hasattr(cosyvoice, 'model') and hasattr(cosyvoice.model, 'token_hop_len'):
            orig_hop = cosyvoice.model.token_hop_len
            hop_env = os.getenv('COSY_TOKEN_HOP')
            new_hop = int(hop_env) if hop_env is not None else 8
            cosyvoice.model.token_hop_len = new_hop  # smaller hop for lower first audio delay
            print(f"[CosyVoice2] token_hop_len: {orig_hop} -> {cosyvoice.model.token_hop_len}")
    except Exception:
        pass

    # Load 16kHz prompt wav generated earlier
    prompt_path = args.prompt_wav
    if not os.path.isabs(prompt_path):
        prompt_path = os.path.abspath(prompt_path)
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt wav not found: {prompt_path}")
    prompt_speech_16k = load_wav(prompt_path, 16000)

    # Texts
    tts_text = args.text
    prompt_text = args.prompt_text

    out_dir = os.path.dirname(__file__)
    i_last = -1

    # Optional warmup to compile CUDA kernels and populate caches, reducing first-chunk latency
    if os.getenv("COSY_WARMUP", "1") == "1":
        try:
            warmup_iters = int(os.getenv("COSY_WARMUP_ITERS", "1"))
            for _i, _out in enumerate(cosyvoice.inference_zero_shot("嗯", "嗯", prompt_speech_16k, stream=True)):
                # Touch tensors to trigger full lazy initialization; drop immediately
                _ = _out.get('tts_speech', None)
                if _i + 1 >= warmup_iters:
                    break
            print("Warmup done (COSY_WARMUP=1).")
        except Exception as _e:
            print(f"Warmup failed: {_e}")

    import time as _time
    t0 = _time.time()
    first_reported = False
    for i, out in enumerate(cosyvoice.inference_zero_shot(tts_text, prompt_text, prompt_speech_16k, stream=True, speed=args.speed)):
        if not first_reported:
            _ttft = (_time.time()-t0)
            print(f"First audio delay: {_ttft:.3f}s")
            # For automated parsers/bench harness
            print(f"TTFT: {_ttft:.3f} s")
            first_reported = True
        wav = out['tts_speech']
        sr = cosyvoice.sample_rate
        out_path = os.path.join(out_dir, f'cosy2_zero_shot_{i}.wav')
        # Save using soundfile to avoid torchaudio dependency
        wav_np = wav.squeeze(0).detach().cpu().numpy()
        sf.write(out_path, wav_np, sr)
        print(f'Wrote {out_path} ({wav.shape[-1]/sr:.2f}s)')
        i_last = i

    # done

    if i_last < 0:
        print('No audio chunks were produced.')
    else:
        print('CosyVoice2 zero-shot synthesis complete.')


if __name__ == '__main__':
    main()

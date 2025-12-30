import os
import sys
import time
from typing import List, Dict, Any

# Optional: force CPU via env
if os.getenv("COSY_FORCE_CPU", "0") == "1":
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

# Ensure local third_party paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
cosy_path = os.path.join(ROOT, 'third_party', 'CosyVoice')
matcha_path = os.path.join(ROOT, 'third_party', 'Matcha-TTS')
if cosy_path not in sys.path:
    sys.path.insert(0, cosy_path)
if matcha_path not in sys.path:
    sys.path.insert(0, matcha_path)

# HF hub compat shim
try:
    import huggingface_hub as hfh  # type: ignore
    if not hasattr(hfh, 'cached_download'):
        from huggingface_hub import hf_hub_download  # type: ignore
        def cached_download(repo_id, filename, cache_dir=None, force_filename=None, force_download=False,
                            proxies=None, etag_timeout=10, resume_download=False, local_files_only=False,
                            use_auth_token=None, revision=None, subfolder=None, mirror=None, **kwargs):
            return hf_hub_download(
                repo_id, filename, subfolder=subfolder, revision=revision, cache_dir=cache_dir,
                local_files_only=local_files_only, force_download=force_download, proxies=proxies,
                etag_timeout=etag_timeout, resume_download=resume_download, token=use_auth_token,
                force_filename=force_filename,
            )
        setattr(hfh, 'cached_download', cached_download)
        print('huggingface_hub.cached_download shimmed via hf_hub_download')
except Exception as e:
    print(f'HF hub compat shim failed: {e}')

import numpy as np
import soundfile as sf
import torch
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav


def stream_and_measure(cosy: CosyVoice2, tts_text: str, prompt_text: str, prompt_wav16k: np.ndarray, lang_tag: str,
                       out_dir: str, gap_warn_threshold: float = 0.25) -> Dict[str, Any]:
    """
    Stream TTS for a single text, measure TTFT and continuity drift.
    Returns metrics and writes a combined WAV file per language at the end.
    """
    # Warmup (optional)
    if os.getenv('COSY_WARMUP', '1') == '1':
        try:
            warmup_iters = int(os.getenv('COSY_WARMUP_ITERS', '1'))
            for i, out in enumerate(cosy.inference_zero_shot("嗯", "嗯", prompt_wav16k, stream=True)):
                _ = out.get('tts_speech', None)
                if i + 1 >= warmup_iters:
                    break
            print(f"[{lang_tag}] Warmup done")
        except Exception as e:
            print(f"[{lang_tag}] Warmup failed: {e}")

    # Timing and buffers
    sr = cosy.sample_rate
    chunks: List[np.ndarray] = []
    t0 = time.time()
    first_ts = None
    prev_ts = t0
    cum_audio = 0.0
    drift_max = 0.0
    rtf_list: List[float] = []
    gap_events: List[float] = []

    # Apply token_hop override only if provided via env
    try:
        if hasattr(cosy, 'model') and hasattr(cosy.model, 'token_hop_len'):
            orig = cosy.model.token_hop_len
            env_hop = os.getenv('COSY_TOKEN_HOP')
            if env_hop is None:
                # Backward compat: also honor COSY_TOKEN_HOP_LEN if present
                env_hop = os.getenv('COSY_TOKEN_HOP_LEN')
            if env_hop is not None:
                new_hop = int(env_hop)
                cosy.model.token_hop_len = max(1, new_hop)
                if cosy.model.token_hop_len != orig:
                    print(f"[{lang_tag}] token_hop_len: {orig} -> {cosy.model.token_hop_len}")
            # First-chunk smaller hop to improve TTFT (optional)
            first_hop_env = os.getenv('COSY_FIRST_HOP') or os.getenv('COSY_FIRST_HOP_LEN')
            if first_hop_env is not None:
                first_hop = max(1, int(first_hop_env))
                main_hop = cosy.model.token_hop_len
                if first_hop != main_hop:
                    setattr(cosy.model, '_cosy_first_hop_len', first_hop)
                    setattr(cosy.model, '_cosy_main_hop_len', main_hop)
                    first_chunks = max(1, int(os.getenv('COSY_FIRST_CHUNKS', '1')))
                    setattr(cosy.model, '_cosy_first_chunks', first_chunks)
                    cosy.model.token_hop_len = first_hop
                    print(f"[{lang_tag}] first-hop override enabled: first {first_chunks} chunk(s) hop={first_hop}, then -> {main_hop}")
    except Exception:
        pass

    # Stream
    # 使用 cross_lingual 模式（不传入 prompt_text，避免其被生成到输出）
    for idx, out in enumerate(cosy.inference_cross_lingual(tts_text, prompt_wav16k, stream=True, text_frontend=False)):
        now = time.time()
        if first_ts is None:
            first_ts = now
            print(f"[{lang_tag}] First audio delay (TTFT): {first_ts - t0:.3f}s")
        wav_t = out['tts_speech']  # torch.Tensor [1, T]
        wav_np = wav_t.squeeze(0).detach().cpu().numpy()
        dur = wav_np.shape[-1] / sr
        chunks.append(wav_np)

        # RTF is provided in logs from model; compute wall-time delta and drift
        wall_delta = now - prev_ts
        cum_audio += dur
        wall_since_first = now - first_ts
        drift = wall_since_first - cum_audio
        drift_max = max(drift_max, drift)
        if drift > gap_warn_threshold:
            gap_events.append(drift)

        # Optional RTF estimate per chunk from our side
        if wall_delta > 1e-6:
            rtf_chunk = wall_delta / dur if dur > 0 else float('inf')
            rtf_list.append(rtf_chunk)
            print(f"[{lang_tag}] chunk#{idx} dur={dur:.2f}s, wallΔ={wall_delta:.3f}s, drift={drift:.3f}s, rtf~{rtf_chunk:.2f}")
        else:
            print(f"[{lang_tag}] chunk#{idx} dur={dur:.2f}s, wallΔ~0, drift={drift:.3f}s")

        prev_ts = now

        # After first N chunks, switch hop back to main_hop if first-hop override is active
        try:
            if hasattr(cosy, 'model') and hasattr(cosy.model, '_cosy_first_hop_len'):
                first_chunks = int(getattr(cosy.model, '_cosy_first_chunks', 1))
                if idx + 1 == first_chunks:
                    main_hop = int(getattr(cosy.model, '_cosy_main_hop_len', cosy.model.token_hop_len))
                    if main_hop != cosy.model.token_hop_len:
                        cosy.model.token_hop_len = max(1, main_hop)
                        print(f"[{lang_tag}] switching hop -> {cosy.model.token_hop_len} after first {first_chunks} chunk(s)")
                        # Clean markers to avoid repeated switches
                        for k in ['_cosy_first_hop_len', '_cosy_main_hop_len', '_cosy_first_chunks']:
                            if hasattr(cosy.model, k):
                                delattr(cosy.model, k)
        except Exception:
            pass

    # Write combined file
    if chunks:
        full = np.concatenate(chunks)
        out_path = os.path.join(out_dir, f"cosy2_stream_{lang_tag}.wav")
        sf.write(out_path, full, sr)
        ttft_val = (first_ts - t0) if first_ts else float('nan')
        print(f"[{lang_tag}] Wrote combined: {out_path} ({full.shape[-1]/sr:.2f}s), TTFT={ttft_val:.3f}s, drift_max={drift_max:.3f}s")
    else:
        print(f"[{lang_tag}] No audio generated")

    return {
        'ttft': (first_ts - t0) if first_ts else None,
        'drift_max': drift_max,
        'rtf_mean': float(np.mean(rtf_list)) if rtf_list else None,
        'gap_events': gap_events,
        'chunks': len(chunks),
    }


def main():
    # Resolve model path: prefer local cache or explicit override to avoid network issues
    model_id = 'iic/CosyVoice2-0.5B'
    override = os.getenv('COSY_MODEL_DIR')
    if override and os.path.exists(override):
        model_id = override
        print(f"Using COSY_MODEL_DIR: {model_id}")
    else:
        # Try ModelScope default cache
        home = os.path.expanduser('~')
        ms_cache = os.path.join(home, '.cache', 'modelscope', 'hub', 'models', 'iic', 'CosyVoice2-0.5B')
        if os.path.exists(ms_cache):
            model_id = ms_cache
            print(f"Using local ModelScope cache: {model_id}")
    # Derive fp16 from env and auto-disable if Torch is forced to CPU to avoid dtype mismatches
    force_cpu = os.getenv('COSY_TORCH_FORCE_CPU', '0') in ('1', 'true', 'True')
    fp16_env = os.getenv('COSY_FP16', '1')
    use_fp16 = (fp16_env in ('1', 'true', 'True')) and (not force_cpu)
    # Optionally enable internal TRT for flow decoder estimator via env COSY_CV2_TRT=1
    load_trt_flag = os.getenv('COSY_CV2_TRT', '0') in ('1', 'true', 'True')
    cosy = CosyVoice2(model_id, load_jit=False, load_trt=load_trt_flag, fp16=use_fp16, use_flow_cache=True)

    # cuDNN autotune
    try:
        torch.backends.cudnn.benchmark = True
    except Exception:
        pass

    # Allow overriding prompt wav and output directory via env
    prompt_env = os.getenv('COSY_PROMPT_WAV')
    if prompt_env and os.path.exists(prompt_env):
        prompt_path = prompt_env
        print(f"Using COSY_PROMPT_WAV: {prompt_path}")
    else:
        prompt_path = os.path.join(os.path.dirname(__file__), 'zero_shot_prompt.wav')
        if prompt_env:
            print(f"COSY_PROMPT_WAV not found, fallback: {prompt_path}")
    prompt_wav16k = load_wav(prompt_path, 16000)

    cases = [
        {
            'tag': 'zh',
            'text': '收到好友从远方寄来的生日礼物，那份意外的惊喜与深深的祝福让我心中充满了甜蜜的快乐，笑容如花儿般绽放。',
            'prompt_text': '你好',  # 短 prompt，匹配语言
        },
        {
            'tag': 'en',
            'text': 'I received a birthday gift from a friend far away. The unexpected surprise and warm wishes filled my heart with joy, and a smile blossomed like a flower.',
            'prompt_text': 'hello',  # 短 prompt，匹配语言
        },
        {
            'tag': 'ja',
            'text': '遠くの友人から誕生日の贈り物が届きました。思いがけない驚きと温かい祝福に心が満たされ、花のような笑顔が咲きました。',
            'prompt_text': 'こんにちは',  # 短 prompt，匹配语言
        },
    ]

    # Optional: override or extend texts for long-form testing
    try:
        # Per-language explicit overrides via env
        zh_env = os.getenv('COSY_TEXT_ZH')
        en_env = os.getenv('COSY_TEXT_EN')
        ja_env = os.getenv('COSY_TEXT_JA')
        # Or via file paths
        zh_file = os.getenv('COSY_TEXT_FILE_ZH')
        en_file = os.getenv('COSY_TEXT_FILE_EN')
        ja_file = os.getenv('COSY_TEXT_FILE_JA')
        def load_if_file(p):
            if p and os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        return f.read().strip()
                except Exception:
                    return None
            return None
        zh_file_txt = load_if_file(zh_file)
        en_file_txt = load_if_file(en_file)
        ja_file_txt = load_if_file(ja_file)
        for c in cases:
            if c['tag'] == 'zh':
                if zh_file_txt: c['text'] = zh_file_txt
                elif zh_env: c['text'] = zh_env
            elif c['tag'] == 'en':
                if en_file_txt: c['text'] = en_file_txt
                elif en_env: c['text'] = en_env
            elif c['tag'] == 'ja':
                if ja_file_txt: c['text'] = ja_file_txt
                elif ja_env: c['text'] = ja_env
        # Repeat factor for long text
        rep = int(os.getenv('COSY_TEXT_REPEAT', '1'))
        if rep > 1:
            for c in cases:
                base = c['text']
                c['text'] = ' '.join([base] * rep)
        # Optional mixed multilingual case when requested via COSY_LANGS includes 'mix'
        langs_env_peek = os.getenv('COSY_LANGS', '')
        if 'mix' in [s.strip() for s in langs_env_peek.split(',') if s.strip()]:
            zh_txt = next((x['text'] for x in cases if x['tag'] == 'zh'), '')
            en_txt = next((x['text'] for x in cases if x['tag'] == 'en'), '')
            ja_txt = next((x['text'] for x in cases if x['tag'] == 'ja'), '')
            mix_text = ' '.join([zh_txt, en_txt, ja_txt]).strip()
            if rep > 1 and mix_text:
                mix_text = ' '.join([mix_text] * 1)  # already repeated within per-lang texts
            cases.append({
                'tag': 'mix',
                'text': mix_text or (zh_txt + ' ' + en_txt + ' ' + ja_txt),
                'prompt_text': '希望你以后能够做的比我还好呦。',
            })
    except Exception as e:
        print(f"Text override setup failed: {e}")

    # Optional filter via COSY_LANGS, e.g., "zh,en" or "ja"
    langs_env = os.getenv('COSY_LANGS')
    if langs_env:
        allow = set([s.strip() for s in langs_env.split(',') if s.strip()])
        cases = [c for c in cases if c['tag'] in allow]

    out_dir = os.getenv('COSY_OUT_DIR') or os.path.dirname(__file__)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception as e:
        print(f"Failed to create out dir {out_dir}: {e}; fallback to script dir")
        out_dir = os.path.dirname(__file__)

    results: Dict[str, Any] = {}
    for c in cases:
        tag = c['tag']
        print(f"\n=== [{tag}] Streaming synthesis start ===")
        res = stream_and_measure(cosy, c['text'], c['prompt_text'], prompt_wav16k, tag, out_dir)
        results[tag] = res
        # Simple continuity verdict
        gaps = res['gap_events']
        if gaps:
            print(f"[{tag}] Continuity risk: {len(gaps)} gap events (max drift {res['drift_max']:.3f}s) > threshold")
        else:
            print(f"[{tag}] Continuity OK: no gaps detected (max drift {res['drift_max']:.3f}s)")

    print("\nSummary:")
    for tag, res in results.items():
        print(f"- {tag}: TTFT={res['ttft']:.3f}s, chunks={res['chunks']}, drift_max={res['drift_max']:.3f}s, rtf_mean={res['rtf_mean']}")


if __name__ == '__main__':
    main()

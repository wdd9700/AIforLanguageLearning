#!/usr/bin/env python3
import sys
import os
import json
import time
import base64
import io
import warnings
from pathlib import Path
import torch
import numpy as np
import soundfile as sf
import torchaudio

# Redirect stdout to stderr for logs, so we can use stdout for JSON
# But we need to keep the original stdout to print JSON
original_stdout = sys.stdout
sys.stdout = sys.stderr

# ============================================================
# Patches
# ============================================================
os.environ.setdefault('PYTORCH_FAKE_TENSOR_ENABLED', '0')
os.environ.setdefault('TORCH_LOGS', '-fake_tensor')
os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'

def _patched_torchaudio_load(filepath, *args, **kwargs):
    data, samplerate = sf.read(filepath)
    tensor = torch.from_numpy(data)
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    else:
        tensor = tensor.transpose(0, 1)
    if tensor.dtype == torch.float64:
        tensor = tensor.float()
    return tensor, samplerate

torchaudio.load = _patched_torchaudio_load

import torch.serialization as torch_ser
_original_torch_load = torch.load

def _patched_torch_load_fix_keys(*args, **kwargs):
    kwargs['weights_only'] = False
    state_dict = _original_torch_load(*args, **kwargs)
    if isinstance(state_dict, dict):
        keys_to_rename = {}
        for key in list(state_dict.keys()):
            if '.spectrogram.window' in key:
                new_key = key.replace('.spectrogram.window', '.window')
                keys_to_rename[key] = new_key
            elif '.mel_scale.fb' in key:
                new_key = key.replace('.mel_scale.fb', '.fb')
                keys_to_rename[key] = new_key
        for old_key, new_key in keys_to_rename.items():
            state_dict[new_key] = state_dict.pop(old_key)
    return state_dict

torch.load = _patched_torch_load_fix_keys
torch_ser.load = _patched_torch_load_fix_keys

from TTS.api import TTS
from TTS.tts.models.xtts import Xtts

_original_xtts_load_checkpoint = Xtts.load_checkpoint
def _patched_xtts_load_checkpoint(self, config, checkpoint_dir=None, checkpoint_path=None, vocab_path=None, eval=False, strict=True, use_deepspeed=False):
    return _original_xtts_load_checkpoint(self, config, checkpoint_dir, checkpoint_path, vocab_path, eval, strict=False, use_deepspeed=use_deepspeed)
Xtts.load_checkpoint = _patched_xtts_load_checkpoint

warnings.filterwarnings('ignore')

class XTTSWrapper:
    def __init__(self, prompt_wav):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[XTTS] Initializing on {self.device}", file=sys.stderr)
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
        self.prompt_wav = prompt_wav
        print(f"[XTTS] Model loaded", file=sys.stderr)

    def synthesize(self, text, language):
        # Use tts_to_file to temp file then read
        # This is safer than direct memory manipulation with XTTS API quirks
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            self.tts.tts_to_file(
                text=text,
                speaker_wav=self.prompt_wav,
                language=language,
                file_path=tmp_path
            )
            
            # Read audio
            with open(tmp_path, "rb") as f:
                audio_data = f.read()
                
            # Encode base64
            b64_audio = base64.b64encode(audio_data).decode('utf-8')
            
            # Send JSON
            # Protocol: {"type": "audio", "data": "base64..."} then {"type": "done"}
            
            msg_audio = json.dumps({"type": "audio", "data": b64_audio})
            original_stdout.write(msg_audio + "\n")
            
            msg_done = json.dumps({"type": "done"})
            original_stdout.write(msg_done + "\n")
            
            original_stdout.flush()
            
        except Exception as e:
            print(f"[XTTS] Error: {e}", file=sys.stderr)
            msg = json.dumps({"type": "error", "message": str(e)})
            original_stdout.write(msg + "\n")
            original_stdout.flush()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

def main():
    prompt_wav = os.getenv('XTTS_PROMPT_WAV')
    if not prompt_wav:
        print("[XTTS] Error: XTTS_PROMPT_WAV not set", file=sys.stderr)
        sys.exit(1)

    try:
        engine = XTTSWrapper(prompt_wav)
    except Exception as e:
        print(f"[XTTS] Init Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("[XTTS] Ready to receive requests", file=sys.stderr)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
                
            data = json.loads(line)
            text = data.get('text')
            language = data.get('language', 'en')
            
            if text:
                engine.synthesize(text, language)
                
        except json.JSONDecodeError:
            print("[XTTS] Invalid JSON", file=sys.stderr)
        except Exception as e:
            print(f"[XTTS] Loop Error: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()

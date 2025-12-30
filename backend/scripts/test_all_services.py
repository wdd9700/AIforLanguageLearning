#!/usr/bin/env python
"""
Test all AI services (TTS, OCR, ASR) using testresources files
"""

import json
import os
import sys
import time
import subprocess
import base64

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PYTHON_EXE = r'C:\Users\74090\Miniconda3\envs\torchnb311\python.exe'

def test_tts():
    """Test TTS service using TTStest.json"""
    print("\n=== Testing TTS Service ===")
    
    # Read test text
    test_file = os.path.join(PROJECT_ROOT, 'testresources', 'TTStest.json')
    with open(test_file, 'r', encoding='utf-8') as f:
        text = f.read().strip()
    
    print(f"Text length: {len(text)} characters")
    print(f"Preview: {text[:100]}...")
    
    # Output path
    output_path = os.path.join(PROJECT_ROOT, 'backend', 'temp', 'tts_test_output.wav')
    
    # XTTS wrapper (stdin/stdout JSON protocol)
    wrapper_path = os.path.join(PROJECT_ROOT, 'backend', 'scripts', 'xtts_wrapper.py')
    prompt_wav = os.path.join(PROJECT_ROOT, 'testresources', 'TTSpromptAudio.wav')

    if not os.path.exists(wrapper_path):
        print(f"✗ XTTS wrapper not found: {wrapper_path}")
        return False
    if not os.path.exists(prompt_wav):
        print(f"✗ Prompt wav not found: {prompt_wav}")
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [PYTHON_EXE, wrapper_path]
    print(f"\nCommand: {' '.join(cmd)}")
    print("\nWaiting for XTTS synthesis (first run may take 1-2 minutes)...")

    t0 = time.time()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env={
            **os.environ,
            'XTTS_PROMPT_WAV': prompt_wav,
            'PYTHONIOENCODING': 'utf-8',
        }
    )

    try:
        # Best-effort wait for readiness
        ready_deadline = time.time() + 30
        while time.time() < ready_deadline:
            if proc.stderr is None:
                break
            line = proc.stderr.readline()
            if not line:
                break
            if 'Ready to receive requests' in line:
                break

        if proc.stdin is None or proc.stdout is None:
            print("✗ XTTS subprocess pipes not available")
            return False

        req = {"text": text, "language": "zh"}
        proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
        proc.stdin.flush()

        audio_bytes = b""
        done = False
        timeout_seconds = 180
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            if msg.get('type') == 'audio':
                audio_bytes += base64.b64decode(msg.get('data', ''))
            elif msg.get('type') == 'done':
                done = True
                break
            elif msg.get('type') == 'error':
                raise RuntimeError(msg.get('message') or msg.get('error') or 'XTTS error')

        elapsed = time.time() - t0
        print(f"\nExecution time: {elapsed:.2f}s")

        if not done:
            print("✗ XTTS did not finish within timeout")
            return False
        if not audio_bytes:
            print("✗ XTTS returned no audio")
            return False

        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        print("\n✓ TTS Success! (XTTS v2)")
        print(f"  Output: {output_path}")
        print(f"  Bytes: {len(audio_bytes)}")
        return True

    except Exception as e:
        print("✗ TTS Failed")
        print(f"error: {e}")
        if proc.stderr is not None:
            err_tail = proc.stderr.read()
            if err_tail:
                print(f"stderr: {err_tail[-2000:]}")
        return False
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def test_ocr():
    """Test OCR service using OCRtest.png"""
    print("\n=== Testing OCR Service ===")
    
    test_image = os.path.join(PROJECT_ROOT, 'testresources', 'OCRtest.png')
    output_dir = os.path.join(PROJECT_ROOT, 'backend', 'temp', 'ocr_output')
    
    if not os.path.exists(test_image):
        print(f"✗ Test image not found: {test_image}")
        return False
    
    os.makedirs(output_dir, exist_ok=True)
    
    wrapper_path = os.path.join(PROJECT_ROOT, 'backend', 'scripts', 'paddleocr_v3_wrapper.py')
    if not os.path.exists(wrapper_path):
        print(f"✗ PaddleOCR wrapper not found: {wrapper_path}")
        return False

    cmd = [PYTHON_EXE, wrapper_path, test_image, 'japan', 'true']

    print(f"Command: {' '.join(cmd)}")
    print("\nRunning OCR (PaddleOCR)...")

    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    print(f"\nExecution time: {elapsed:.2f}s")
    print(f"Return code: {result.returncode}")

    if result.returncode != 0:
        print("✗ OCR Failed")
        print(f"stderr: {result.stderr[-2000:]}")
        return False

    try:
        stdout = result.stdout
        json_start = stdout.find('{')
        json_end = stdout.rfind('}')
        if json_start == -1 or json_end == -1:
            raise ValueError('No JSON found in OCR stdout')
        payload = json.loads(stdout[json_start:json_end + 1])
        if not payload.get('success'):
            raise ValueError(payload.get('error') or 'OCR failed')

        out_json = os.path.join(output_dir, 'ocr_result.json')
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        lines = payload.get('results') or []
        text = "\n".join([str(l.get('text', '')) for l in lines]).strip()
        out_txt = os.path.join(output_dir, 'ocr_result.txt')
        with open(out_txt, 'w', encoding='utf-8') as f:
            f.write(text)

        print("✓ OCR Success! (PaddleOCR)")
        print(f"  Lines: {payload.get('count', len(lines))}")
        print(f"  Text saved: {out_txt}")
        print(f"  JSON saved: {out_json}")
        return True
    except Exception as e:
        print("✗ OCR Output Parse Failed")
        print(f"error: {e}")
        return False


def test_asr():
    """Test ASR service using ASRtest.wav"""
    print("\n=== Testing ASR Service ===")
    
    test_audio = os.path.join(PROJECT_ROOT, 'testresources', 'ASRtest.wav')
    output_dir = os.path.join(PROJECT_ROOT, 'backend', 'temp', 'asr_output')
    
    if not os.path.exists(test_audio):
        print(f"✗ Test audio not found: {test_audio}")
        return False
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Call whisper
    cmd = [
        'whisper', test_audio,
        '--model', 'turbo',
        '--device', 'cuda',
        '--output_dir', output_dir,
        '--output_format', 'json'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("\nRunning ASR...")
    
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    
    print(f"\nExecution time: {elapsed:.2f}s")
    print(f"Return code: {result.returncode}")
    
    if result.returncode == 0:
        print("✓ ASR Success!")
        print(f"stdout: {result.stdout}")
        return True
    else:
        print("✗ ASR Failed")
        print(f"stderr: {result.stderr}")
    
    return False


def main():
    """Run all tests"""
    print("=" * 80)
    print("AI Services Integration Test")
    print("=" * 80)
    
    results = {}
    
    # Test TTS (most complex)
    results['TTS'] = test_tts()
    
    # Test OCR
    results['OCR'] = test_ocr()
    
    # Test ASR
    results['ASR'] = test_asr()
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    for service, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{service:10s}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("=" * 80))
    if all_passed:
        print("All tests PASSED!")
        return 0
    else:
        print("Some tests FAILED!")
        return 1


if __name__ == '__main__':
    sys.exit(main())

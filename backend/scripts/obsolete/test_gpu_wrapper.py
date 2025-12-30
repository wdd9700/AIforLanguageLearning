"""
Test CosyVoice2 GPU wrapper with project test resources
"""
import sys
import os

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'backend', 'scripts'))

import json

# Read test text
test_json_path = os.path.join(ROOT, 'testresources', 'TTStest.json')
prompt_audio_path = os.path.join(ROOT, 'testresources', 'TTSpromptAudio.wav')
output_path = os.path.join(ROOT, 'backend', 'temp', 'gpu_test_output.wav')

print(f"Reading test text from: {test_json_path}")
with open(test_json_path, 'r', encoding='utf-8') as f:
    test_text = f.read().strip()

print(f"Test text length: {len(test_text)} characters")
print(f"Prompt audio: {prompt_audio_path}")
print(f"Output path: {output_path}")

# Import wrapper
from cosyvoice_wrapper_gpu import synthesize

print("\n=== Starting GPU TTS Test ===")
print(f"Note: Using default prompt audio from wrapper (TTSpromptAudio.wav should be set in env)")

# Set environment variables for GPU optimization
os.environ['COSY_PROMPT_AUDIO'] = prompt_audio_path
os.environ['COSY_TOKEN_HOP'] = '32'  # Optimal RTF
os.environ['COSY_WARMUP'] = '1'
os.environ['COSY_AMP_DTYPE'] = 'bf16'

result = synthesize(
    text=test_text[:200],  # 测试前200字符
    output_path=output_path,
    prompt_text="",  # Zero-shot mode
    speed=1.0,
    stream=False  # Merge all chunks
)

print(f"\n=== Test Result ===")
print(json.dumps(result, indent=2))
print(f"\nOutput file exists: {os.path.exists(output_path)}")
if os.path.exists(output_path):
    print(f"Output file size: {os.path.getsize(output_path)} bytes")

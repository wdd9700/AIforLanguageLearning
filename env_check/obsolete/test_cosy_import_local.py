import sys, traceback
from pathlib import Path
base = Path(r"e:/projects/AiforForiegnLanguageLearning")
# Add local repos to sys.path
sys.path.insert(0, str(base/"third_party"/"CosyVoice"))
sys.path.insert(0, str(base/"third_party"/"Matcha-TTS"))
print("sys.path patched for local CosyVoice & Matcha-TTS")

try:
    import cosyvoice
    print("cosyvoice import ok (local path)")
    from cosyvoice.cli.cosyvoice import CosyVoice2
    print("CosyVoice2 class ok (local path)")
except Exception as e:
    print("ERROR:", e)
    traceback.print_exc()
    raise SystemExit(1)

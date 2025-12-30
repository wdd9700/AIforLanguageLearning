from __future__ import annotations

import time
from pathlib import Path


def main() -> int:
    wav = Path(__file__).resolve().parents[2] / "testresources" / "ASRtest.wav"
    print("wav:", wav)
    print("exists:", wav.exists())

    from faster_whisper import WhisperModel

    start = time.time()
    model = WhisperModel(
        "tiny",
        device="cpu",
        compute_type="int8",
        download_root=str(Path.home() / ".cache" / "whisper"),
    )
    print("model loaded in", round(time.time() - start, 2), "s")

    start = time.time()
    segments, info = model.transcribe(
        str(wav),
        language="en",
        beam_size=1,
        vad_filter=True,
    )
    text_parts: list[str] = []
    for seg in segments:
        t = (seg.text or "").strip()
        if t:
            text_parts.append(t)
    full = " ".join(text_parts).strip()

    print("transcribe in", round(time.time() - start, 2), "s")
    print("detected:", getattr(info, "language", None), getattr(info, "language_probability", None))
    print("TEXT:")
    print(full)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

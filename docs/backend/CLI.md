# CLI 调用手册（Whisper / PaddleOCR / LM Studio / XTTS v2）

本手册汇总了在 Windows PowerShell 环境下集成调用的常用命令模板与参数要点，便于在软件中按需拼装命令并执行。

注意：若使用 GPU，请提前在正确的 Python/Conda 环境中安装带 CUDA 的 PyTorch；在本机上，你也可以通过设置环境变量选择设备，例如 `$env:TORCH_DEVICE="cuda"` 或 `"cpu"`。

目录：
- Whisper 语音转写/翻译（命令行）
- PaddleOCR（命令行/后端集成）
- LM Studio 本地模型管理与服务（命令行）
- XTTS v2 文本转语音（后端集成说明）

---

## Whisper（命令行）

快速示例（将音频转写为字幕与 JSON）：

```powershell
# 单文件转写（输出 txt/vtt/srt/tsv/json 全部格式至指定目录）
whisper "E:\path\to\input.wav" --model turbo --device cpu --output_dir "E:\out\whisper" --output_format all

# 指定任务为翻译（X->English），并显式指定源语言中文
whisper "E:\path\to\input.wav" --task translate --language zh --model turbo --device cpu --output_dir "E:\out\whisper"

# 批处理多个音频（通配符）
whisper "E:\path\to\audios\*.wav" --model turbo --device cpu --output_dir "E:\out\whisper"
```

常用参数摘录：
- `--model`：模型名（默认 turbo）
- `--device`：推理设备（cpu|cuda...；如装有 CUDA 版 PyTorch 可用 `cuda`）
- `--task`：`transcribe`（转写）或 `translate`（翻译到英文）
- `--language`：源语言，留空可自动检测
- `--output_dir`：输出目录；`--output_format`：输出格式（`txt|vtt|srt|tsv|json|all`）

完整帮助（原始 usage）：

usage: whisper [-h] [--model MODEL] [--model_dir MODEL_DIR] [--device DEVICE] [--output_dir OUTPUT_DIR]
               [--output_format {txt,vtt,srt,tsv,json,all}] [--verbose VERBOSE] [--task {transcribe,translate}]
               [--language {af,am,ar,as,az,ba,be,bg,bn,bo,br,bs,ca,cs,cy,da,de,el,en,es,et,eu,fa,fi,fo,fr,gl,gu,ha,haw,he,hi,hr,ht,hu,hy,id,is,it,ja,jw,ka,kk,km,kn,ko,la,lb,ln,lo,lt,lv,mg,mi,mk,ml,mn,mr,ms,mt,my,ne,nl,nn,no,oc,pa,pl,ps,pt,ro,ru,sa,sd,si,sk,sl,sn,so,sq,sr,su,sv,sw,ta,te,tg,th,tk,tl,tr,tt,uk,ur,uz,vi,yi,yo,yue,zh,Afrikaans,Albanian,Amharic,Arabic,Armenian,Assamese,Azerbaijani,Bashkir,Basque,Belarusian,Bengali,Bosnian,Breton,Bulgarian,Burmese,Cantonese,Castilian,Catalan,Chinese,Croatian,Czech,Danish,Dutch,English,Estonian,Faroese,Finnish,Flemish,French,Galician,Georgian,German,Greek,Gujarati,Haitian,Haitian Creole,Hausa,Hawaiian,Hebrew,Hindi,Hungarian,Icelandic,Indonesian,Italian,Japanese,Javanese,Kannada,Kazakh,Khmer,Korean,Lao,Latin,Latvian,Letzeburgesch,Lingala,Lithuanian,Luxembourgish,Macedonian,Malagasy,Malay,Malayalam,Maltese,Mandarin,Maori,Marathi,Moldavian,Moldovan,Mongolian,Myanmar,Nepali,Norwegian,Nynorsk,Occitan,Panjabi,Pashto,Persian,Polish,Portuguese,Punjabi,Pushto,Romanian,Russian,Sanskrit,Serbian,Shona,Sindhi,Sinhala,Sinhalese,Slovak,Slovenian,Somali,Spanish,Sundanese,Swahili,Swedish,Tagalog,Tajik,Tamil,Tatar,Telugu,Thai,Tibetan,Turkish,Turkmen,Ukrainian,Urdu,Uzbek,Valencian,Vietnamese,Welsh,Yiddish,Yoruba}]
               [--temperature TEMPERATURE] [--best_of BEST_OF] [--beam_size BEAM_SIZE] [--patience PATIENCE]
               [--length_penalty LENGTH_PENALTY] [--suppress_tokens SUPPRESS_TOKENS] [--initial_prompt INITIAL_PROMPT]
               [--carry_initial_prompt CARRY_INITIAL_PROMPT] [--condition_on_previous_text CONDITION_ON_PREVIOUS_TEXT]
               [--fp16 FP16] [--temperature_increment_on_fallback TEMPERATURE_INCREMENT_ON_FALLBACK]
               [--compression_ratio_threshold COMPRESSION_RATIO_THRESHOLD] [--logprob_threshold LOGPROB_THRESHOLD]
               [--no_speech_threshold NO_SPEECH_THRESHOLD] [--word_timestamps WORD_TIMESTAMPS]
               [--prepend_punctuations PREPEND_PUNCTUATIONS] [--append_punctuations APPEND_PUNCTUATIONS]
               [--highlight_words HIGHLIGHT_WORDS] [--max_line_width MAX_LINE_WIDTH] [--max_line_count MAX_LINE_COUNT]
               [--max_words_per_line MAX_WORDS_PER_LINE] [--threads THREADS] [--clip_timestamps CLIP_TIMESTAMPS]
               [--hallucination_silence_threshold HALLUCINATION_SILENCE_THRESHOLD]
               audio [audio ...]

positional arguments:
  audio                 audio file(s) to transcribe

options:
  -h, --help            show this help message and exit
  --model MODEL         name of the Whisper model to use (default: turbo)
  --model_dir MODEL_DIR
                        the path to save model files; uses ~/.cache/whisper by default (default: None)
  --device DEVICE       device to use for PyTorch inference (default: cpu)
  --output_dir, -o OUTPUT_DIR
                        directory to save the outputs (default: .)
  --output_format, -f {txt,vtt,srt,tsv,json,all}
                        format of the output file; if not specified, all available formats will be produced (default:
                        all)
  --verbose VERBOSE     whether to print out the progress and debug messages (default: True)
  --task {transcribe,translate}
                        whether to perform X->X speech recognition ('transcribe') or X->English translation
                        ('translate') (default: transcribe)
  --language {af,am,ar,as,az,ba,be,bg,bn,bo,br,bs,ca,cs,cy,da,de,el,en,es,et,eu,fa,fi,fo,fr,gl,gu,ha,haw,he,hi,hr,ht,hu,hy,id,is,it,ja,jw,ka,kk,km,kn,ko,la,lb,ln,lo,lt,lv,mg,mi,mk,ml,mn,mr,ms,mt,my,ne,nl,nn,no,oc,pa,pl,ps,pt,ro,ru,sa,sd,si,sk,sl,sn,so,sq,sr,su,sv,sw,ta,te,tg,th,tk,tl,tr,tt,uk,ur,uz,vi,yi,yo,yue,zh,Afrikaans,Albanian,Amharic,Arabic,Armenian,Assamese,Azerbaijani,Bashkir,Basque,Belarusian,Bengali,Bosnian,Breton,Bulgarian,Burmese,Cantonese,Castilian,Catalan,Chinese,Croatian,Czech,Danish,Dutch,English,Estonian,Faroese,Finnish,Flemish,French,Galician,Georgian,German,Greek,Gujarati,Haitian,Haitian Creole,Hausa,Hawaiian,Hebrew,Hindi,Hungarian,Icelandic,Indonesian,Italian,Japanese,Javanese,Kannada,Kazakh,Khmer,Korean,Lao,Latin,Latvian,Letzeburgesch,Lingala,Lithuanian,Luxembourgish,Macedonian,Malagasy,Malay,Malayalam,Maltese,Mandarin,Maori,Marathi,Moldavian,Moldovan,Mongolian,Myanmar,Nepali,Norwegian,Nynorsk,Occitan,Panjabi,Pashto,Persian,Polish,Portuguese,Punjabi,Pushto,Romanian,Russian,Sanskrit,Serbian,Shona,Sindhi,Sinhala,Sinhalese,Slovak,Slovenian,Somali,Spanish,Sundanese,Swahili,Swedish,Tagalog,Tajik,Tamil,Tatar,Telugu,Thai,Tibetan,Turkish,Turkmen,Ukrainian,Urdu,Uzbek,Valencian,Vietnamese,Welsh,Yiddish,Yoruba}
                        language spoken in the audio, specify None to perform language detection (default: None)
  --temperature TEMPERATURE
                        temperature to use for sampling (default: 0)
  --best_of BEST_OF     number of candidates when sampling with non-zero temperature (default: 5)
  --beam_size BEAM_SIZE
                        number of beams in beam search, only applicable when temperature is zero (default: 5)
  --patience PATIENCE   optional patience value to use in beam decoding, as in https://arxiv.org/abs/2204.05424, the
                        default (1.0) is equivalent to conventional beam search (default: None)
  --length_penalty LENGTH_PENALTY
                        optional token length penalty coefficient (alpha) as in https://arxiv.org/abs/1609.08144, uses
                        simple length normalization by default (default: None)
  --suppress_tokens SUPPRESS_TOKENS
                        comma-separated list of token ids to suppress during sampling; '-1' will suppress most special
                        characters except common punctuations (default: -1)
  --initial_prompt INITIAL_PROMPT
                        optional text to provide as a prompt for the first window. (default: None)
  --carry_initial_prompt CARRY_INITIAL_PROMPT
                        if True, prepend initial_prompt to every internal decode() call. May reduce the effectiveness
                        of condition_on_previous_text (default: False)
  --condition_on_previous_text CONDITION_ON_PREVIOUS_TEXT
                        if True, provide the previous output of the model as a prompt for the next window; disabling
                        may make the text inconsistent across windows, but the model becomes less prone to getting
                        stuck in a failure loop (default: True)
  --fp16 FP16           whether to perform inference in fp16; True by default (default: True)
  --temperature_increment_on_fallback TEMPERATURE_INCREMENT_ON_FALLBACK
                        temperature to increase when falling back when the decoding fails to meet either of the
                        thresholds below (default: 0.2)
  --compression_ratio_threshold COMPRESSION_RATIO_THRESHOLD
                        if the gzip compression ratio is higher than this value, treat the decoding as failed (default:
                        2.4)
  --logprob_threshold LOGPROB_THRESHOLD
                        if the average log probability is lower than this value, treat the decoding as failed (default:
                        -1.0)
  --no_speech_threshold NO_SPEECH_THRESHOLD
                        if the probability of the <|nospeech|> token is higher than this value AND the decoding has
                        failed due to `logprob_threshold`, consider the segment as silence (default: 0.6)
  --word_timestamps WORD_TIMESTAMPS
                        (experimental) extract word-level timestamps and refine the results based on them (default:
                        False)
  --prepend_punctuations PREPEND_PUNCTUATIONS
                        if word_timestamps is True, merge these punctuation symbols with the next word (default:
                        "'“¿([{-)
  --append_punctuations APPEND_PUNCTUATIONS
                        if word_timestamps is True, merge these punctuation symbols with the previous word (default:
                        "'.。,，!！?？:：”)]}、)
  --highlight_words HIGHLIGHT_WORDS
                        (requires --word_timestamps True) underline each word as it is spoken in srt and vtt (default:
                        False)
  --max_line_width MAX_LINE_WIDTH
                        (requires --word_timestamps True) the maximum number of characters in a line before breaking
                        the line (default: None)
  --max_line_count MAX_LINE_COUNT
                        (requires --word_timestamps True) the maximum number of lines in a segment (default: None)
  --max_words_per_line MAX_WORDS_PER_LINE
                        (requires --word_timestamps True, no effect with --max_line_width) the maximum number of words
                        in a segment (default: None)
  --threads THREADS     number of threads used by torch for CPU inference; supercedes MKL_NUM_THREADS/OMP_NUM_THREADS
                        (default: 0)
  --clip_timestamps CLIP_TIMESTAMPS
                        comma-separated list start,end,start,end,... timestamps (in seconds) of clips to process, where
                        the last end timestamp defaults to the end of the file (default: 0)
  --hallucination_silence_threshold HALLUCINATION_SILENCE_THRESHOLD
                        (requires --word_timestamps True) skip silent periods longer than this threshold (in seconds)
                        when a possible hallucination is detected (default: None)

---

## PaddleOCR（命令行/后端集成）

当前工程 OCR 主线为 PaddleOCR，通过 Python 包装脚本输出 JSON，Node 后端通过子进程调用。

关键文件：
- `backend/src/services/ocr.service.ts`
- `backend/scripts/paddleocr_v3_wrapper.py`

命令行快速验证（单张图片）：

```powershell
# 用法: python paddleocr_v3_wrapper.py <image_path_or_base64> [lang] [use_angle_cls]
python .\backend\scripts\paddleocr_v3_wrapper.py "E:\path\to\image.png" japan true
```

说明：
- `lang` 常用：`japan` / `ch` / `en`
- `use_angle_cls`：是否启用文本方向分类（true/false）

集成联测建议：

```powershell
# 运行一键联测（包含 OCR）
python .\backend\scripts\test_all_services.py
```

---

## LM Studio（命令行）

检查状态 / 启动/停止本地 API 服务：

```powershell
lms status
lms server start
# ...使用后
lms server stop
```

模型管理：
```powershell
# 列出已下载模型
lms ls --json

# 加载模型（最大化 GPU 加速，无需确认）
lms load "E:\path\to\model.gguf" -y

# 查看已加载模型
lms ps --json

# 卸载全部
lms unload --all
```

备注：`lms` 随 LM Studio 一并提供（0.2.22+）。若命令不可用，先执行：
```powershell
npx lmstudio install-cli
```

---

## XTTS v2（后端集成说明）

当前工程的 TTS 主路径为 XTTS v2（Coqui TTS），由 Node.js 后端拉起一个 Python 子进程完成推理。

关键文件：
- `backend/src/services/tts.service.ts`：进程管理与流式拼接
- `backend/scripts/xtts_wrapper.py`：Python 推理包装（stdin/stdout JSON 协议）

本地手动验证建议：

```powershell
# 运行一键联测（包含 TTS/OCR/ASR）
python .\backend\scripts\test_all_services.py
```

如果只想验证 TTS：

```powershell
# 需要准备 prompt wav（默认使用 testresources/TTSpromptAudio.wav）
python .\backend\scripts\test_all_services.py
```

---

## 集成调用模板（占位符）

在软件中可使用以下模板并替换占位符：

- Whisper 转写（全格式）：
```powershell
whisper "{audio_path}" --model {model} --device {device} --output_dir "{out_dir}" --output_format all
```

- PaddleOCR（单图）：
```powershell
python .\backend\scripts\paddleocr_v3_wrapper.py "{image_path}" {lang} {use_angle_cls}
```

- LM Studio 启动与加载：
```powershell
lms server start ; lms load "{model_path}" -y
```

如需进一步扩展 HTTP 调用（LM Studio 本地服务）或批处理调度，可在应用层封装命令与结果文件路径的约定，按需解析输出 JSON/字幕等产物。

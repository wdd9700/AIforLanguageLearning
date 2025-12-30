#!/usr/bin/env python3
"""
Faster-Whisper ASR 封装脚本 (CPU 优化版本)
基于 AMD 9950X3D CCD0 (3D V-Cache) 优化
性能: 加载 7.12s, RTF=0.130x
"""

import sys
import os
import json
import time
import warnings
import psutil

# 抑制警告
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# ===== CPU 优化配置 =====
# 1. CPU 亲和性: 绑定到 CCD0 (核心 0-15, 3D V-Cache)
try:
    process = psutil.Process()
    # AMD 9950X3D: CCD0 = 核心 0-15 (带 3D V-Cache)
    process.cpu_affinity([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    print(f"[INFO] CPU 亲和性设置成功: {process.cpu_affinity()}", file=sys.stderr)
except Exception as e:
    print(f"[WARN] CPU 亲和性设置失败: {e}", file=sys.stderr)

# 2. OpenMP/MKL 线程配置 (16 线程)
os.environ["OMP_NUM_THREADS"] = "16"
os.environ["MKL_NUM_THREADS"] = "16"
os.environ["OMP_PROC_BIND"] = "close"
os.environ["OMP_PLACES"] = "cores"
os.environ["KMP_AFFINITY"] = "granularity=fine,compact,1,0"

from faster_whisper import WhisperModel

class FasterWhisperASR:
    def __init__(self, model_size="small", compute_type="int8", cpu_threads=16, num_workers=4):
        """
        初始化 Faster-Whisper 模型
        
        Args:
            model_size: 模型大小 (tiny/base/small/medium/large-v3)
            compute_type: 计算类型 (int8/float32)
            cpu_threads: CPU 线程数
            num_workers: 并行解码数
        """
        self.model_size = model_size
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.num_workers = num_workers
        self.model = None
        
    def load_model(self):
        """加载模型"""
        start_time = time.time()
        print(f"[INFO] 开始加载模型: {self.model_size}, compute_type={self.compute_type}", file=sys.stderr)
        
        self.model = WhisperModel(
            self.model_size,
            device="cpu",
            compute_type=self.compute_type,
            cpu_threads=self.cpu_threads,
            num_workers=self.num_workers
        )
        
        load_time = time.time() - start_time
        print(f"[INFO] 模型加载完成: {load_time:.2f}s", file=sys.stderr)
        return load_time
    
    def transcribe(self, audio_path, language=None, beam_size=5, vad_filter=True):
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码 (None=自动检测)
            beam_size: 束搜索大小
            vad_filter: 是否启用 VAD 过滤
        
        Returns:
            dict: 转录结果 {text, language, segments, timing}
        """
        if not self.model:
            raise RuntimeError("模型未加载,请先调用 load_model()")
        
        start_time = time.time()
        print(f"[INFO] 开始转录: {audio_path}", file=sys.stderr)
        
        # 转录
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            word_timestamps=True
        )
        
        # 收集结果
        full_text = []
        segment_list = []
        
        for segment in segments:
            full_text.append(segment.text)
            segment_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
        
        transcribe_time = time.time() - start_time
        
        result = {
            "text": " ".join(full_text).strip(),
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": segment_list,
            "timing": {
                "transcribe_time": transcribe_time,
                "rtf": transcribe_time / info.duration if info.duration > 0 else 0
            }
        }
        
        print(f"[INFO] 转录完成: {transcribe_time:.2f}s, RTF={result['timing']['rtf']:.3f}x", file=sys.stderr)
        return result

def main():
    """
    命令行入口
    
    用法:
        python faster_whisper_wrapper.py <audio_path> [options]
        
    选项:
        --model <size>      模型大小 (默认: small)
        --language <code>   语言代码 (默认: auto)
        --compute-type <type> 计算类型 (默认: int8)
        --cpu-threads <num>   CPU 线程数 (默认: 16)
    """
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "缺少音频文件路径参数"
        }))
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    # 解析选项
    model_size = "small"
    language = None
    compute_type = "int8"
    cpu_threads = 16
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--model" and i + 1 < len(sys.argv):
            model_size = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--language" and i + 1 < len(sys.argv):
            language = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--compute-type" and i + 1 < len(sys.argv):
            compute_type = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--cpu-threads" and i + 1 < len(sys.argv):
            cpu_threads = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    try:
        # 初始化 ASR
        asr = FasterWhisperASR(
            model_size=model_size,
            compute_type=compute_type,
            cpu_threads=cpu_threads
        )
        
        # 加载模型
        load_time = asr.load_model()
        
        # 转录
        result = asr.transcribe(audio_path, language=language)
        
        # 输出 JSON 结果
        output = {
            "success": True,
            "text": result["text"],
            "language": result["language"],
            "duration": result["duration"],
            "load_time": load_time,
            "transcribe_time": result["timing"]["transcribe_time"],
            "rtf": result["timing"]["rtf"],
            "segments": result["segments"]
        }
        
        print(json.dumps(output, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

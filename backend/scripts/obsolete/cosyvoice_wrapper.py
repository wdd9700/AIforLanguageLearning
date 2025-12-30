"""
CosyVoice2 TTS 包装脚本（零样本模式）
用于从 Node.js 调用 CosyVoice2-0.5B 生成语音

使用方式:
python cosyvoice_wrapper.py --text "要合成的文本" --output output.wav [--voice default] [--speed 1.0]
"""

import sys
import os
import argparse
import json

# 添加 CosyVoice 路径
COSYVOICE_ROOT = r'E:\models\CosyVoice\CosyVoice'
sys.path.insert(0, COSYVOICE_ROOT)
sys.path.insert(0, os.path.join(COSYVOICE_ROOT, 'third_party', 'Matcha-TTS'))

try:
    from cosyvoice.cli.cosyvoice import CosyVoice2
    import torch
    import scipy.io.wavfile as wavfile
    import numpy as np
except ImportError as e:
    print(json.dumps({"error": f"Import failed: {str(e)}. Check CosyVoice installation."}), file=sys.stderr)
    sys.exit(1)

# 全局模型实例（避免重复加载）
_model = None

def get_model():
    """获取或初始化模型"""
    global _model
    if _model is None:
        # 强制 CPU 模式（避免 RTX 5080 CUDA 兼容性问题）
        torch.cuda.is_available = lambda: False
        
        model_path = os.path.join(COSYVOICE_ROOT, 'pretrained_models', 'CosyVoice2-0.5B')
        try:
            _model = CosyVoice2(
                model_path,
                load_jit=False,
                load_trt=False,
                load_vllm=False,
                fp16=False  # CPU 模式不使用 FP16
            )
        except Exception as e:
            print(json.dumps({"error": f"Model load failed: {str(e)}"}), file=sys.stderr)
            sys.exit(1)
    return _model

def synthesize(text: str, output_path: str, voice: str = "default", speed: float = 1.0):
    """
    合成语音（使用 CosyVoice2 零样本模式）
    
    Args:
        text: 要合成的文本
        output_path: 输出音频文件路径
        voice: 语音风格（保留接口，实际使用参考音频）
        speed: 语速（暂未实现，保留接口）
    """
    try:
        model = get_model()
        
        # 加载参考音频（16kHz，用于零样本克隆）
        reference_audio_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'assets', 
            'reference_voice.wav'
        )
        
        if not os.path.exists(reference_audio_path):
            raise FileNotFoundError(f"Reference audio not found: {reference_audio_path}")
        
        # 加载参考音频（使用 scipy 避免 FFmpeg 依赖）
        import scipy.io.wavfile as wavfile_reader
        sample_rate, audio_data = wavfile_reader.read(reference_audio_path)
        
        # 转换为 torch tensor
        audio_float = audio_data.astype(np.float32) / 32768.0
        prompt_speech_16k = torch.from_numpy(audio_float).unsqueeze(0)
        
        # 使用零样本模式（无需预定义 speaker ID）
        prompt_text = ""  # 参考文本为空
        
        # 调用 inference_zero_shot
        for i, result in enumerate(model.inference_zero_shot(
            text,
            prompt_text,
            prompt_speech_16k,
            stream=False
        )):
            # 保存音频（使用 scipy 避免 FFmpeg 依赖）
            audio_numpy = result['tts_speech'].cpu().numpy().squeeze()
            audio_int16 = (audio_numpy * 32767).astype(np.int16)
            wavfile.write(output_path, model.sample_rate, audio_int16)
            break  # 只取第一个结果
        
        # 返回成功信息
        print(json.dumps({
            "success": True,
            "output": output_path,
            "sample_rate": model.sample_rate
        }))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='CosyVoice2 TTS Wrapper')
    parser.add_argument('--text', required=True, help='Text to synthesize')
    parser.add_argument('--output', required=True, help='Output audio file path')
    parser.add_argument('--voice', default='default', help='Voice style (placeholder)')
    parser.add_argument('--speed', type=float, default=1.0, help='Speech speed (placeholder)')
    
    args = parser.parse_args()
    
    synthesize(args.text, args.output, args.voice, args.speed)

if __name__ == '__main__':
    main()

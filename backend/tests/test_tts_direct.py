"""
直接测试 TTS 服务（绕过复杂的脚本，使用后端服务管理器）

目的：
1. 验证 TTS 是否在 GPU 上运行
2. 验证是否使用正确的 prompt 音频
3. 验证文本是否被正确生成（不被分句）
"""

import sys
import os
from pathlib import Path

# 添加后端路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir / 'src'))

import asyncio
import json

# 测试用例
TEST_CASES = [
    {
        'lang': 'zh',
        'text': '人工智能正在改变我们的生活方式，从语音识别到自然语言处理，技术的进步让人机交互变得越来越自然。'
    },
    {
        'lang': 'en',
        'text': 'Artificial intelligence is revolutionizing how we interact with technology, making voice recognition and natural language processing more accurate than ever before.'
    },
    {
        'lang': 'ja',
        'text': '音声認識技術の進歩により、私たちはより自然な方法でコンピュータと対話できるようになりました。'
    }
]


async def test_tts_direct():
    """直接测试 TTS 服务"""
    from managers.service_manager import ServiceManager
    
    manager = ServiceManager()
    
    print("="*80)
    print("直接 TTS 服务测试")
    print("="*80)
    
    # 初始化服务
    print("\n初始化 TTS 服务...")
    await manager.probeTTS()
    
    if not manager.ttsReady:
        print("❌ TTS 服务未就绪")
        return
    
    print("✅ TTS 服务已就绪\n")
    
    # 测试每个语言
    for i, test_case in enumerate(TEST_CASES, 1):
        lang = test_case['lang']
        text = test_case['text']
        
        print(f"\n{'='*80}")
        print(f"测试 {i}: {lang.upper()}")
        print(f"{'='*80}")
        print(f"文本: {text}\n")
        
        # 调用 TTS
        print(f"生成音频中...")
        
        try:
            result = await manager.invokeTTS({
                'text': text,
                'lang': lang,
                'stream': False  # 先测试非流式
            })
            
            if result.get('success'):
                audio_path = result.get('audio_path')
                duration = result.get('duration', 0)
                
                print(f"✅ 生成成功!")
                print(f"   音频文件: {audio_path}")
                print(f"   时长: {duration:.2f}s")
                
                # 使用 ASR 识别验证
                print(f"\n验证音频内容（ASR 识别）...")
                
                # 调用 ASR
                asr_result = await manager.invokeASR({
                    'audio': audio_path
                })
                
                if asr_result.get('success'):
                    recognized_text = asr_result.get('text', '')
                    print(f"✅ ASR 识别结果:")
                    print(f"   {recognized_text}")
                    
                    # 简单对比
                    original_lower = text.lower().replace(' ', '')
                    recognized_lower = recognized_text.lower().replace(' ', '')
                    
                    # 计算字符重叠
                    original_chars = set(original_lower)
                    recognized_chars = set(recognized_lower)
                    overlap = len(original_chars & recognized_chars) / len(original_chars) if original_chars else 0
                    
                    print(f"\n   字符重叠率: {overlap*100:.1f}%")
                    
                    if overlap > 0.5:
                        print(f"   ✅ 匹配度良好")
                    else:
                        print(f"   ⚠️ 匹配度较低")
                else:
                    print(f"❌ ASR 识别失败: {asr_result.get('error')}")
            else:
                print(f"❌ TTS 生成失败: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("测试完成")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    asyncio.run(test_tts_direct())

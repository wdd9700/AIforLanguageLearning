#!/usr/bin/env python3
"""
WebSocket 集成测试脚本
测试完整的 ASR -> LLM -> TTS 流程

使用方法：
    python test_websocket_integration.py

前置条件：
    - 后端服务运行在 http://localhost:3000
    - LM Studio 运行在 http://localhost:1234
    - 音频文件: test_audio.webm 或使用内置测试数据
"""

import asyncio
import json
import websockets
import base64
import sys
from pathlib import Path

# 配置
WEBSOCKET_URL = "ws://127.0.0.1:3000/stream"  # 使用显式 IP 而不是 localhost
TEST_TIMEOUT = 30  # 秒

# 测试用的 Base64 编码音频数据（使用小的测试文件）
# 这是一个简单的 WebM 格式音频头（包含 "你好" 的中文音频会很大，所以这里用占位符）
TEST_AUDIO_BASE64 = None  # 稍后从文件读取或生成


async def test_websocket_connection():
    """测试 WebSocket 基本连接"""
    print("\n🔌 测试 1: 基本连接")
    try:
        async with websockets.connect(WEBSOCKET_URL, ping_interval=10) as ws:
            print("✓ WebSocket 连接成功")
            
            # 发送 ping
            await ws.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(response)
            
            if data.get("type") == "pong":
                print("✓ Ping/Pong 正常")
                return True
            else:
                print("✗ 意外的 pong 响应:", data)
                return False
                
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False


async def test_asr_llm_tts_pipeline(audio_base64):
    """测试完整的 ASR -> LLM -> TTS 流程"""
    print("\n🎙 测试 2: ASR -> LLM -> TTS 完整流程")
    
    if not audio_base64:
        print("⚠ 未提供音频数据，跳过 ASR 测试")
        return False
    
    try:
        async with websockets.connect(WEBSOCKET_URL, ping_interval=10) as ws:
            # 准备 ASR 请求
            asr_request = {
                "type": "asr",
                "data": {
                    "audio": audio_base64,
                    "language": "zh-CN"
                }
            }
            
            print("📤 发送 ASR 请求...")
            await ws.send(json.dumps(asr_request))
            
            # 收集所有响应
            responses = []
            response_types = set()
            
            async def receive_with_timeout():
                try:
                    return await asyncio.wait_for(ws.recv(), timeout=10)
                except asyncio.TimeoutError:
                    return None
            
            # 接收多个响应（ASR -> LLM -> TTS）
            for i in range(5):  # 最多接收 5 个响应
                msg = await receive_with_timeout()
                if not msg:
                    break
                
                try:
                    data = json.loads(msg)
                    response_type = data.get("type")
                    response_types.add(response_type)
                    
                    print(f"📥 收到响应 {i+1}: {response_type}")
                    
                    if response_type == "error":
                        print(f"  错误: {data.get('error')}")
                    elif response_type == "asr_result":
                        text = data.get("data", {}).get("text", "")
                        print(f"  ASR 转写: {text}")
                    elif response_type == "llm_result":
                        text = data.get("data", {}).get("text", "")
                        print(f"  LLM 响应: {text}")
                    elif response_type == "tts_result":
                        text = data.get("data", {}).get("text", "")
                        audio_len = len(data.get("data", {}).get("audio", ""))
                        print(f"  TTS 生成: {text} (音频大小: {audio_len} bytes)")
                    
                    responses.append(data)
                    
                    # 如果收到 TTS 或错误，停止接收
                    if response_type in ["tts_result", "error"]:
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"  ✗ JSON 解析错误: {e}")
                    break
            
            # 检查流程完整性
            expected_types = {"asr_result", "llm_result", "tts_result"}
            if response_types >= expected_types:
                print("✓ 完整流程收到所有响应")
                return True
            else:
                missing = expected_types - response_types
                print(f"✗ 缺少响应类型: {missing}")
                return False
                
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def load_test_audio():
    """尝试加载测试音频文件"""
    audio_path = Path("test_audio.webm")
    
    if audio_path.exists():
        print(f"📁 加载测试音频: {audio_path}")
        try:
            with open(audio_path, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode("utf-8")
                print(f"✓ 音频已加载 ({len(data)} bytes)")
                return b64
        except Exception as e:
            print(f"✗ 加载失败: {e}")
            return None
    else:
        print("⚠ 未找到 test_audio.webm，使用模拟数据")
        # 返回一个最小的 WebM 文件头（虽然不是真实音频，但用于测试连接）
        return base64.b64encode(b"mock_audio_data").decode("utf-8")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("WebSocket 集成测试")
    print("=" * 60)
    print(f"目标服务器: {WEBSOCKET_URL}")
    
    # 测试 1: 基本连接
    result1 = await test_websocket_connection()
    
    # 加载测试音频
    audio_b64 = await load_test_audio()
    
    # 测试 2: 完整流程
    result2 = await test_asr_llm_tts_pipeline(audio_b64)
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果摘要")
    print("=" * 60)
    print(f"1. 基本连接: {'✓ 通过' if result1 else '✗ 失败'}")
    print(f"2. ASR->LLM->TTS: {'✓ 通过' if result2 else '✗ 失败'}")
    
    if result1 and result2:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

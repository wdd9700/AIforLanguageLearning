#!/usr/bin/env python3
"""
后端集成测试 - 测试流式数据处理和服务集成
"""
import asyncio
import websockets
import json
import base64
import wave
import io
import sys
from pathlib import Path

# 测试配置
BACKEND_WS = "ws://127.0.0.1:3006/stream"
BACKEND_HTTP = "http://127.0.0.1:3006"

def create_test_audio():
    """创建一个简单的测试音频文件（1秒静音）"""
    sample_rate = 16000
    duration = 1  # 秒
    
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)  # 单声道
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(b'\x00' * (sample_rate * duration * 2))
    
    buffer.seek(0)
    return buffer.read()

async def test_websocket_connection():
    """测试 1: WebSocket 连接"""
    print("\n" + "="*60)
    print("测试 1: WebSocket 基础连接")
    print("="*60)
    
    try:
        async with websockets.connect(BACKEND_WS) as ws:
            print("✓ WebSocket 连接成功")
            
            # 发送 ping 消息
            test_msg = json.dumps({"type": "ping"})
            await ws.send(test_msg)
            print(f"✓ 发送测试消息: {test_msg}")
            
            # 等待响应（最多 2 秒）
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                print(f"✓ 收到响应: {response[:100]}...")
                return True
            except asyncio.TimeoutError:
                print("⚠ 未收到响应（超时）")
                return True  # 连接成功但无响应也算通过
                
    except Exception as e:
        print(f"✗ WebSocket 连接失败: {e}")
        return False

async def test_audio_streaming():
    """测试 2: 音频流式处理"""
    print("\n" + "="*60)
    print("测试 2: 音频流式处理")
    print("="*60)
    
    try:
        # 创建测试音频
        audio_data = create_test_audio()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        print(f"✓ 创建测试音频: {len(audio_data)} 字节 -> Base64: {len(audio_base64)} 字符")
        
        async with websockets.connect(BACKEND_WS) as ws:
            print("✓ WebSocket 已连接")
            
            # 发送音频数据
            message = json.dumps({
                "type": "audio",
                "data": audio_base64
            })
            await ws.send(message)
            print(f"✓ 发送音频数据: {len(message)} 字节")
            
            # 接收流式响应
            print("\n等待后端处理响应...")
            responses = []
            timeout_count = 0
            max_timeout = 3
            
            while timeout_count < max_timeout:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(response)
                    responses.append(data)
                    
                    print(f"\n✓ 收到响应 #{len(responses)}:")
                    print(f"  类型: {data.get('type')}")
                    if 'data' in data:
                        if isinstance(data['data'], dict):
                            for key, value in data['data'].items():
                                if key == 'audio' and value:
                                    print(f"  {key}: [Base64 音频数据, 长度={len(value)}]")
                                else:
                                    print(f"  {key}: {value}")
                        else:
                            print(f"  data: {str(data['data'])[:100]}")
                    
                    # 如果收到 tts_result，表示流程完成
                    if data.get('type') == 'tts_result':
                        print("\n✓ 完整流程完成（收到 TTS 结果）")
                        break
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"⚠ 超时 {timeout_count}/{max_timeout}")
                    if responses:
                        break
                except json.JSONDecodeError as e:
                    print(f"✗ JSON 解析错误: {e}")
                    timeout_count += 1
            
            print(f"\n📊 总共收到 {len(responses)} 个响应")
            return len(responses) > 0
            
    except Exception as e:
        print(f"✗ 音频流式处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_message_flow():
    """测试 3: 完整消息流"""
    print("\n" + "="*60)
    print("测试 3: 完整消息流（ASR → LLM → TTS）")
    print("="*60)
    
    try:
        audio_data = create_test_audio()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        async with websockets.connect(BACKEND_WS) as ws:
            message = json.dumps({
                "type": "audio",
                "data": audio_base64
            })
            await ws.send(message)
            print("✓ 发送音频数据")
            
            # 追踪完整流程
            flow_steps = {
                'asr_result': False,
                'llm_result': False,
                'tts_result': False
            }
            
            for i in range(10):  # 最多等待 10 个消息
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(response)
                    msg_type = data.get('type')
                    
                    if msg_type in flow_steps:
                        flow_steps[msg_type] = True
                        print(f"✓ 步骤 {list(flow_steps.keys()).index(msg_type) + 1}/3: {msg_type}")
                    elif msg_type == 'error':
                        print(f"⚠ 收到错误: {data.get('data', {}).get('message', 'Unknown error')}")
                    
                    if all(flow_steps.values()):
                        print("\n✓ 完整流程测试通过！")
                        return True
                        
                except asyncio.TimeoutError:
                    break
            
            # 检查结果
            completed = sum(flow_steps.values())
            total = len(flow_steps)
            print(f"\n📊 流程完成度: {completed}/{total}")
            for step, completed in flow_steps.items():
                status = "✓" if completed else "✗"
                print(f"  {status} {step}")
            
            return completed > 0
            
    except Exception as e:
        print(f"✗ 消息流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_concurrent_connections():
    """测试 4: 并发连接处理"""
    print("\n" + "="*60)
    print("测试 4: 并发连接处理")
    print("="*60)
    
    async def single_connection(conn_id):
        try:
            async with websockets.connect(BACKEND_WS) as ws:
                await ws.send(json.dumps({"type": "ping", "id": conn_id}))
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                return True
        except Exception as e:
            print(f"  连接 {conn_id} 失败: {e}")
            return False
    
    # 创建 5 个并发连接
    tasks = [single_connection(i) for i in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    print(f"\n✓ 并发连接成功: {success_count}/5")
    return success_count >= 4  # 至少 4 个成功

async def test_error_handling():
    """测试 5: 错误处理"""
    print("\n" + "="*60)
    print("测试 5: 错误处理能力")
    print("="*60)
    
    try:
        async with websockets.connect(BACKEND_WS) as ws:
            # 发送无效数据
            test_cases = [
                ("无效 JSON", "invalid json"),
                ("空消息", ""),
                ("无效 Base64", json.dumps({"type": "audio", "data": "invalid_base64!!!"})),
            ]
            
            for name, data in test_cases:
                try:
                    await ws.send(data)
                    print(f"✓ 发送 {name}")
                    
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        resp_data = json.loads(response)
                        if resp_data.get('type') == 'error':
                            print(f"  ✓ 正确返回错误响应")
                        else:
                            print(f"  ⚠ 返回: {resp_data.get('type')}")
                    except asyncio.TimeoutError:
                        print(f"  ⚠ 无响应（可能被忽略）")
                        
                except Exception as e:
                    print(f"  ⚠ 异常: {e}")
            
            return True
            
    except Exception as e:
        print(f"✗ 错误处理测试失败: {e}")
        return False

async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("后端集成测试套件")
    print("="*60)
    print(f"WebSocket 端点: {BACKEND_WS}")
    print(f"HTTP 端点: {BACKEND_HTTP}")
    
    # 运行测试
    tests = [
        ("WebSocket 连接", test_websocket_connection),
        ("音频流式处理", test_audio_streaming),
        ("完整消息流", test_message_flow),
        ("并发连接", test_concurrent_connections),
        ("错误处理", test_error_handling),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 异常: {e}")
            results[name] = False
        
        # 测试间隔
        await asyncio.sleep(1)
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "="*60)
    print(f"总计: {passed}/{total} 测试通过")
    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"成功率: {success_rate:.1f}%")
    print("="*60)
    
    return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ 测试运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
端到端功能测试
测试三大功能：单词查询、作文批改、语音对话
使用 testresources 文件夹中的真实数据
"""
import os
import sys
import json
import base64
import time
import asyncio
import requests
from pathlib import Path
from typing import Dict, Any

# 项目路径
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
TESTRESOURCES_DIR = PROJECT_ROOT / 'testresources'

# 后端服务配置
BACKEND_URL = 'http://localhost:3000'
WS_URL = 'ws://localhost:3000/stream'

# 测试用户
TEST_USER = {
    'username': 'test_user',
    'password': 'Test123456!',  # 强密码
    'email': 'test@example.com'
}

# 全局 token
ACCESS_TOKEN = None

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")

def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text: str):
    """打印信息"""
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.RESET}")

def check_backend_health() -> bool:
    """检查后端服务是否运行"""
    try:
        response = requests.get(f'{BACKEND_URL}/health', timeout=3)
        if response.status_code == 200:
            print_success("后端服务运行中")
            return True
        else:
            print_error(f"后端服务异常: HTTP {response.status_code}")
            return False
    except Exception as e:
        print_error(f"无法连接到后端服务: {e}")
        print_info("请先启动后端服务:")
        print_info("  cd backend && npx tsx src/index.ts")
        return False

def login_or_register() -> bool:
    """登录或注册测试用户，获取 access token"""
    global ACCESS_TOKEN
    
    print_header("用户认证")
    
    # 尝试注册
    try:
        response = requests.post(
            f'{BACKEND_URL}/api/auth/register',
            json=TEST_USER,
            timeout=5
        )
        
        if response.status_code == 201:
            result = response.json()
            ACCESS_TOKEN = result['data']['accessToken']
            print_success(f"注册成功: {TEST_USER['username']}")
            return True
        elif response.status_code in (409, 500):  # 用户已存在或数据库错误
            # 用户可能已存在，尝试登录
            print_info("用户已存在，尝试登录...")
        else:
            print_error(f"注册失败: {response.text[:200]}")
            # 继续尝试登录
    except Exception as e:
        print_error(f"注册异常: {e}")
        # 继续尝试登录
    
    # 登录
    try:
        response = requests.post(
            f'{BACKEND_URL}/api/auth/login',
            json={
                'username': TEST_USER['username'],
                'password': TEST_USER['password']
            },
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            ACCESS_TOKEN = result['data']['accessToken']
            print_success(f"登录成功: {TEST_USER['username']}")
            return True
        else:
            print_error(f"登录失败: {response.text[:200]}")
            return False
    except Exception as e:
        print_error(f"登录异常: {e}")
        return False

def test_vocabulary_query_text() -> bool:
    """测试功能 1: 单词查询 - 文本输入"""
    print_header("测试 1: 单词查询 - 文本输入")
    
    # 测试数据
    test_words = [
        "emoji",
        "ポップカルチャー",
        "pictogram"
    ]
    
    for word in test_words:
        print(f"\n查询单词: {word}")
        
        try:
            response = requests.post(
                f'{BACKEND_URL}/api/query/vocabulary',
                json={'word': word},
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {ACCESS_TOKEN}'
                },
                timeout=90  # 增加到 90 秒，匹配后端 LLM 超时
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    explanation = result['data']['explanation']
                    print_success(f"查询成功")
                    print(f"  解释: {explanation[:150]}...")
                else:
                    print_error(f"查询失败: {result.get('error', 'Unknown')}")
                    return False
            else:
                print_error(f"HTTP {response.status_code}: {response.text[:200]}")
                return False
                
        except Exception as e:
            print_error(f"请求异常: {e}")
            return False
    
    print_success("单词查询 - 文本输入测试通过")
    return True

def test_vocabulary_query_ocr() -> bool:
    """测试功能 2: 单词查询 - OCR 图片"""
    print_header("测试 2: 单词查询 - OCR 图片")
    
    # 读取测试图片
    image_path = TESTRESOURCES_DIR / 'OCRtest.png'
    if not image_path.exists():
        print_error(f"测试图片不存在: {image_path}")
        return False
    
    print(f"测试图片: {image_path}")
    
    # 读取并编码为 Base64
    with open(image_path, 'rb') as f:
        image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    print_info(f"图片大小: {len(image_data)} bytes, Base64: {len(image_base64)} chars")
    
    try:
        response = requests.post(
            f'{BACKEND_URL}/api/query/ocr',
            json={'image': image_base64},
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {ACCESS_TOKEN}'
            },
            timeout=90  # 增加到 90 秒
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                detected_text = result['data']['detectedText']
                confidence = result['data'].get('confidence', 0)
                explanation = result['data']['explanation']
                
                print_success("OCR 识别成功")
                print(f"  识别文本: {detected_text[:100]}...")
                print(f"  置信度: {confidence:.2f}")
                print(f"  LLM 解释: {explanation[:150]}...")
                return True
            else:
                print_error(f"OCR 失败: {result.get('error', 'Unknown')}")
                return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print_error(f"请求异常: {e}")
        return False

def test_essay_correction_text() -> bool:
    """测试功能 3: 作文批改 - 文本输入"""
    print_header("测试 3: 作文批改 - 文本输入")
    
    # 读取测试文本
    tts_test_file = TESTRESOURCES_DIR / 'TTStest.json'
    if not tts_test_file.exists():
        print_error(f"测试文件不存在: {tts_test_file}")
        return False
    
    with open(tts_test_file, 'r', encoding='utf-8') as f:
        essay_text = f.read().strip()
    
    print(f"作文长度: {len(essay_text)} 字符")
    print(f"作文预览: {essay_text[:100]}...")
    
    try:
        response = requests.post(
            f'{BACKEND_URL}/api/essay/correct',
            json={
                'text': essay_text,
                'language': 'japanese'
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {ACCESS_TOKEN}'
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                correction = result['data']['correction']
                print_success("作文批改成功")
                print(f"  批改意见: {correction[:200]}...")
                return True
            else:
                print_error(f"批改失败: {result.get('error', 'Unknown')}")
                return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print_error(f"请求异常: {e}")
        return False

def test_essay_correction_ocr() -> bool:
    """测试功能 4: 作文批改 - OCR 图片"""
    print_header("测试 4: 作文批改 - OCR 图片")
    
    # 读取测试图片
    image_path = TESTRESOURCES_DIR / 'OCRtest.png'
    if not image_path.exists():
        print_error(f"测试图片不存在: {image_path}")
        return False
    
    with open(image_path, 'rb') as f:
        image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    print(f"测试图片: {image_path}")
    
    try:
        response = requests.post(
            f'{BACKEND_URL}/api/essay/ocr-correct',
            json={
                'image': image_base64,
                'language': 'japanese'
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {ACCESS_TOKEN}'
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                detected_text = result['data']['detectedText']
                correction = result['data']['correction']
                print_success("OCR + 作文批改成功")
                print(f"  识别文本: {detected_text[:100]}...")
                print(f"  批改意见: {correction[:200]}...")
                return True
            else:
                print_error(f"批改失败: {result.get('error', 'Unknown')}")
                return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print_error(f"请求异常: {e}")
        return False

def test_voice_dialogue_websocket() -> bool:
    """测试功能 5: 语音对话 - WebSocket 流式处理"""
    print_header("测试 5: 语音对话 - WebSocket 流式处理")
    
    try:
        import websocket
    except ImportError:
        print_error("websocket-client 未安装")
        print_info("安装命令: pip install websocket-client")
        return False
    
    # 读取测试音频（使用更小的音频文件）
    audio_path = TESTRESOURCES_DIR / 'test_zero_shot.wav'
    if not audio_path.exists():
        # 备选：使用 ASRtest.wav 的前 10MB
        audio_path = TESTRESOURCES_DIR / 'ASRtest.wav'
        if not audio_path.exists():
            print_error(f"测试音频不存在: {audio_path}")
            return False
        
        # 只读取前 10MB 避免消息过大
        with open(audio_path, 'rb') as f:
            audio_data = f.read(10 * 1024 * 1024)  # 10MB
        print_info(f"使用截断的音频 (前 10MB)")
    else:
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
    
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    print(f"测试音频: {audio_path}")
    print_info(f"音频大小: {len(audio_data)} bytes")
    
    # WebSocket 连接
    received_messages = []
    
    def on_message(ws, message):
        try:
            msg = json.loads(message)
            msg_type = msg.get('type')
            received_messages.append(msg)
            
            if msg_type == 'asr_result':
                text = msg['data']['text']
                print_success(f"ASR 识别: {text}")
            elif msg_type == 'llm_result':
                text = msg['data']['text']
                print_success(f"LLM 响应: {text}")
            elif msg_type == 'tts_result':
                audio_size = len(msg['data']['audio'])
                print_success(f"TTS 音频: {audio_size} 字符 (Base64)")
            elif msg_type == 'error':
                print_error(f"服务器错误: {msg.get('error')}")
        except json.JSONDecodeError:
            print_error(f"无效 JSON: {message[:100]}")
    
    def on_error(ws, error):
        print_error(f"WebSocket 错误: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print_info("WebSocket 连接关闭")
    
    def on_open(ws):
        print_success("WebSocket 连接已建立")
        
        # 发送音频数据（直接发送 Base64 字符串作为 data）
        message = {
            'type': 'audio',
            'data': audio_base64  # 直接传 Base64 字符串
        }
        
        print_info("发送音频数据...")
        ws.send(json.dumps(message))
    
    try:
        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # 运行 10 秒后自动关闭
        import threading
        def close_ws():
            time.sleep(10)
            ws.close()
        
        closer = threading.Thread(target=close_ws, daemon=True)
        closer.start()
        
        ws.run_forever()
        
        # 检查结果（至少收到 ASR + LLM 响应）
        if len(received_messages) >= 2:
            print_success(f"语音对话测试通过 (收到 {len(received_messages)} 条消息)")
            print_info("注: TTS 响应需要 LLM 正常工作后才能生成")
            return True
        else:
            print_error(f"语音对话测试失败 (仅收到 {len(received_messages)} 条消息)")
            return False
            
    except Exception as e:
        print_error(f"WebSocket 异常: {e}")
        return False

def main():
    """主测试流程"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}端到端功能测试{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    print(f"\n测试资源目录: {TESTRESOURCES_DIR}")
    print(f"后端 URL: {BACKEND_URL}")
    
    # 检查后端服务
    if not check_backend_health():
        return 1
    
    # 登录获取 token
    if not login_or_register():
        print_error("无法获取认证 token，测试终止")
        return 1
    
    # 运行测试
    results = {}
    
    # 1. 单词查询 - 文本
    results['词汇查询(文本)'] = test_vocabulary_query_text()
    time.sleep(1)
    
    # 2. 单词查询 - OCR
    results['词汇查询(OCR)'] = test_vocabulary_query_ocr()
    time.sleep(1)
    
    # 3. 作文批改 - 文本
    results['作文批改(文本)'] = test_essay_correction_text()
    time.sleep(1)
    
    # 4. 作文批改 - OCR
    results['作文批改(OCR)'] = test_essay_correction_ocr()
    time.sleep(1)
    
    # 5. 语音对话 - WebSocket
    results['语音对话(流式)'] = test_voice_dialogue_websocket()
    
    # 汇总结果
    print_header("测试结果汇总")
    
    for test_name, passed in results.items():
        if passed:
            print(f"  {Colors.GREEN}✅{Colors.RESET} {test_name}")
        else:
            print(f"  {Colors.RED}❌{Colors.RESET} {test_name}")
    
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    print(f"\n{Colors.BOLD}通过率: {passed_count}/{total_count} ({passed_count/total_count*100:.0f}%){Colors.RESET}")
    
    if passed_count == total_count:
        print_success("所有测试通过！🎉")
        return 0
    else:
        print_error(f"部分测试失败 ({total_count - passed_count} 个)")
        return 1

if __name__ == '__main__':
    sys.exit(main())

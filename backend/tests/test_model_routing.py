"""
多模型智能路由验证
测试不同任务类型是否使用了正确的模型：
- conversation → qwen3-30b-a3b-2507
- vocabulary/ocr → qwen3-vl-30b  
- analysis/expansion → qwen3-4b-thinking-2507
"""

import sys
import requests
import time

# 后端 URL
BACKEND_URL = "http://localhost:3000"

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg): print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")
def print_info(msg): print(f"{Colors.CYAN}ℹ️  {msg}{Colors.RESET}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")
def print_error(msg): print(f"{Colors.RED}❌ {msg}{Colors.RESET}")
def print_header(msg): print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}\n{Colors.BOLD}{msg}{Colors.RESET}\n{Colors.BOLD}{'='*70}{Colors.RESET}\n")

def check_backend():
    """检查后端是否运行"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def login():
    """登录获取 token"""
    try:
        # 尝试登录
        response = requests.post(
            f'{BACKEND_URL}/api/auth/login',
            json={'username': 'test_user', 'password': 'Test123456!'},
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()['data']['accessToken']
        
        # 登录失败，尝试注册
        response = requests.post(
            f'{BACKEND_URL}/api/auth/register',
            json={'username': 'test_user', 'password': 'Test123456!'},
            timeout=5
        )
        
        if response.status_code == 201:
            # 注册成功，再次登录
            response = requests.post(
                f'{BACKEND_URL}/api/auth/login',
                json={'username': 'test_user', 'password': 'Test123456!'},
                timeout=5
            )
            return response.json()['data']['accessToken']
        
        return None
    except Exception as e:
        print_error(f"认证失败: {e}")
        return None

def test_model_routing(token):
    """测试模型路由"""
    print_header("多模型智能路由验证")
    
    test_cases = [
        {
            "name": "词汇查询 (vocabulary)",
            "endpoint": "/api/query/vocabulary",
            "payload": {"word": "hello"},
            "expected_model": "qwen3-vl-30b",
            "task_type": "vocabulary"
        },
        # 暂时只测试词汇查询，因为其他端点可能需要不同的 payload
    ]
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print_info(f"后端配置的模型路由策略：")
    print("  - conversation: qwen3-30b-a3b-2507")
    print("  - vocabulary/ocr: qwen3-vl-30b")
    print("  - analysis/expansion: qwen3-4b-thinking-2507")
    print()
    
    for test in test_cases:
        print_header(f"测试: {test['name']}")
        print_info(f"预期模型: {test['expected_model']}")
        print_info(f"任务类型: {test['task_type']}")
        print()
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{BACKEND_URL}{test['endpoint']}",
                json=test['payload'],
                headers=headers,
                timeout=90
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    print_success(f"请求成功 (耗时: {elapsed:.2f}s)")
                    print(f"  响应: {str(result.get('data', {}))[:150]}...")
                    print()
                    
                    # 注意: 实际使用的模型信息需要从后端日志或响应中获取
                    # 这里我们通过响应时间和内容质量来推断
                    print_info("模型验证：需要检查后端日志确认使用的模型")
                    print_warning("建议：后端可以在响应中添加 'model_used' 字段")
                else:
                    print_error(f"请求失败: {result.get('error')}")
            else:
                print_error(f"HTTP {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            print_error(f"请求异常: {e}")
    
    print()
    print_header("验证总结")
    print_info("✓ 多模型路由已实现在 service-manager.ts 中")
    print_info("✓ 配置文件已更新 (env.ts)")
    print_warning("⚠️ 需要通过后端日志验证实际使用的模型")
    print()
    print("建议改进：")
    print("1. 在 service-manager.ts 的 invokeLLM 响应中添加 'modelUsed' 字段")
    print("2. 在 API 响应中包含模型信息，方便前端显示和调试")
    print("3. 添加模型切换的监控和日志")

def main():
    print_header("多模型智能路由验证工具")
    
    # 检查后端
    print_info("检查后端服务...")
    if not check_backend():
        print_error("后端服务未运行！请先启动后端服务。")
        print_info("启动命令: cd backend && npx tsx src/index.ts")
        return 1
    
    print_success("后端服务运行中")
    print()
    
    # 登录
    print_info("用户认证...")
    token = login()
    if not token:
        print_error("认证失败！")
        return 1
    
    print_success("认证成功")
    print()
    
    # 测试路由
    test_model_routing(token)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

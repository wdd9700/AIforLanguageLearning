#!/usr/bin/env python3
"""
服务诊断工具 - 检查所有外部服务状态
"""
import requests
import subprocess
import sys
from pathlib import Path

def check_http_service(name, url, timeout=5):
    """检查 HTTP 服务"""
    print(f"\n检查 {name}...")
    print(f"  URL: {url}")
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print(f"  ✓ 状态: 正常 (HTTP {response.status_code})")
            return True, response.json() if 'json' in response.headers.get('content-type', '') else response.text[:100]
        else:
            print(f"  ⚠ 状态: HTTP {response.status_code}")
            return False, None
    except requests.exceptions.ConnectionError:
        print(f"  ✗ 状态: 无法连接")
        return False, None
    except requests.exceptions.Timeout:
        print(f"  ✗ 状态: 连接超时")
        return False, None
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False, None

def check_lm_studio():
    """详细检查 LM Studio"""
    print("\n" + "="*60)
    print("LM Studio 诊断")
    print("="*60)
    
    # 检查 API 可用性
    ok, _ = check_http_service("LM Studio API", "http://localhost:1234/v1/models")
    
    if ok:
        # 获取模型列表
        try:
            response = requests.get("http://localhost:1234/v1/models")
            models = response.json().get('data', [])
            
            print(f"\n  可用模型: {len(models)} 个")
            print(f"\n  模型列表:")
            
            target_model = "qwen/qwen3-30b-a3b-2507"
            found_target = False
            
            for model in models:
                model_id = model.get('id', 'unknown')
                loaded = model.get('loaded', False)
                status = "✓ 已加载" if loaded else "○ 未加载"
                
                if model_id == target_model:
                    found_target = True
                    print(f"    {status} {model_id} ← 目标模型")
                else:
                    print(f"    {status} {model_id}")
            
            if not found_target:
                print(f"\n  ⚠ 未找到目标模型: {target_model}")
                print(f"  建议: 在 LM Studio 中下载此模型")
                return False
            
            # 检查是否有已加载的模型
            loaded_models = [m for m in models if m.get('loaded')]
            if loaded_models:
                print(f"\n  ✓ 已加载模型: {len(loaded_models)} 个")
                for m in loaded_models:
                    print(f"    • {m.get('id')}")
                return True
            else:
                print(f"\n  ⚠ 没有已加载的模型")
                print(f"  建议: 在 LM Studio 中:")
                print(f"    1. 打开 Chat 或 Playground 标签")
                print(f"    2. 选择模型: {target_model}")
                print(f"    3. 点击 Load/Start 按钮")
                return False
                
        except Exception as e:
            print(f"\n  ✗ 获取模型列表失败: {e}")
            return False
    
    return False

def check_backend():
    """检查后端服务"""
    print("\n" + "="*60)
    print("后端服务诊断")
    print("="*60)
    
    ok, data = check_http_service("后端 Health", "http://localhost:3000/health")
    if ok:
        print(f"  响应: {data}")
    
    return ok

def check_python_services():
    """检查 Python 服务（ASR/TTS）"""
    print("\n" + "="*60)
    print("Python 服务诊断")
    print("="*60)
    
    # 检查 Python 环境
    print("\n检查 Python 环境...")
    try:
        result = subprocess.run(
            ['python', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"  ✓ Python: {result.stdout.strip()}")
    except Exception as e:
        print(f"  ✗ Python 不可用: {e}")
        return False
    
    # 检查关键包
    packages = ['torch', 'faster_whisper', 'numpy']
    print(f"\n检查关键 Python 包...")
    all_ok = True
    
    for package in packages:
        try:
            result = subprocess.run(
                ['python', '-c', f'import {package}; print({package}.__version__)'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"  ✓ {package}: {version}")
            else:
                print(f"  ✗ {package}: 未安装")
                all_ok = False
        except Exception as e:
            print(f"  ✗ {package}: 检查失败 ({e})")
            all_ok = False
    
    return all_ok

def main():
    """运行所有诊断"""
    print("="*60)
    print("服务诊断工具")
    print("="*60)
    
    results = {}
    
    # 检查后端
    results['后端'] = check_backend()
    
    # 检查 LM Studio
    results['LM Studio'] = check_lm_studio()
    
    # 检查 Python 服务
    results['Python 服务'] = check_python_services()
    
    # 汇总结果
    print("\n" + "="*60)
    print("诊断结果汇总")
    print("="*60)
    
    for name, ok in results.items():
        status = "✓ 正常" if ok else "✗ 异常"
        print(f"  {status} - {name}")
    
    all_ok = all(results.values())
    
    if all_ok:
        print("\n✓ 所有服务正常！可以开始测试")
        return 0
    else:
        print("\n⚠ 部分服务异常，请按照上述建议修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())

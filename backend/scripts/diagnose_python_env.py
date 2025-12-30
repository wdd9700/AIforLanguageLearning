#!/usr/bin/env python3
"""
项目架构和 Python 环境诊断工具
检查所有 AI 服务的 Python 环境和脚本配置
"""
import os
import sys
import json
import subprocess
from pathlib import Path

def run_command(cmd, timeout=5):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'code': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_python_env(name, python_path):
    """检查 Python 环境"""
    print(f"\n{'='*60}")
    print(f"检查 {name} Python 环境")
    print(f"{'='*60}")
    
    # 检查 Python 可执行文件
    if not os.path.exists(python_path):
        print(f"❌ Python 不存在: {python_path}")
        return False
    
    print(f"✓ Python 路径: {python_path}")
    
    # 检查 Python 版本
    result = run_command(f'"{python_path}" --version')
    if result['success']:
        print(f"✓ Python 版本: {result['stdout']}")
    else:
        print(f"❌ 无法获取版本: {result.get('error', 'Unknown')}")
        return False
    
    # 检查关键包
    packages = {
        'OCR': ['paddleocr', 'paddlepaddle'],
        'ASR': ['faster-whisper', 'numpy'],
        'TTS': ['torch', 'torchaudio', 'TTS', 'onnxruntime']
    }
    
    if name in packages:
        print(f"\n检查 {name} 依赖包:")
        for pkg in packages[name]:
            result = run_command(f'"{python_path}" -c "import {pkg.replace("-", "_")}; print({pkg.replace("-", "_")}.__version__)"')
            if result['success']:
                print(f"  ✓ {pkg}: {result['stdout']}")
            else:
                print(f"  ❌ {pkg}: 未安装或导入失败")
    
    return True

def check_script(name, script_path):
    """检查 Python 脚本"""
    print(f"\n检查 {name} 脚本:")
    
    if not os.path.exists(script_path):
        print(f"  ❌ 脚本不存在: {script_path}")
        return False
    
    print(f"  ✓ 脚本路径: {script_path}")
    
    # 检查脚本大小
    size = os.path.getsize(script_path)
    print(f"  ✓ 文件大小: {size} bytes")
    
    return True

def main():
    print("="*60)
    print("AI 语言学习系统 - Python 环境诊断")
    print("="*60)
    
    # 项目路径
    backend_dir = Path(__file__).parent
    scripts_dir = backend_dir / 'scripts'
    
    print(f"\n项目目录:")
    print(f"  Backend: {backend_dir}")
    print(f"  Scripts: {scripts_dir}")
    
    # 从 .env 读取配置（简化版本）
    env_configs = {
        'OCR': {
            'python': 'C:/Users/74090/Miniconda3/py313/envs/ocr/python.exe',
            'script': scripts_dir / 'paddleocr_v3_wrapper.py',
            'description': 'PaddleOCR v3.3.1 (CPU)'
        },
        'ASR': {
            'python': 'C:/Users/74090/Miniconda3/py313/envs/asr/python.exe',
            'script': scripts_dir / 'faster_whisper_wrapper.py',
            'description': 'Faster-Whisper (CPU, AMD 9950X3D 优化)'
        },
        'TTS': {
            'python': 'C:/Users/74090/Miniconda3/envs/torchnb311/python.exe',
            'script': scripts_dir / 'xtts_wrapper.py',
            'description': 'XTTS v2 (Python wrapper, long-running subprocess)'
        }
    }
    
    results = {}
    
    for name, config in env_configs.items():
        print(f"\n\n{'#'*60}")
        print(f"# {name}: {config['description']}")
        print(f"{'#'*60}")
        
        python_ok = check_python_env(name, config['python'])
        script_ok = check_script(name, str(config['script']))
        
        results[name] = {
            'python_path': config['python'],
            'python_ok': python_ok,
            'script_path': str(config['script']),
            'script_ok': script_ok,
            'status': '✓ 正常' if (python_ok and script_ok) else '❌ 异常'
        }
    
    # 汇总结果
    print(f"\n\n{'='*60}")
    print("诊断汇总")
    print(f"{'='*60}")
    
    for name, result in results.items():
        print(f"\n{name}:")
        print(f"  状态: {result['status']}")
        print(f"  Python: {result['python_path']}")
        print(f"  脚本: {result['script_path']}")
    
    # 检查 LM Studio
    print(f"\n\n{'='*60}")
    print("LLM 服务 (LM Studio)")
    print(f"{'='*60}")
    
    lms_check = run_command('lms --version')
    if lms_check['success']:
        print(f"✓ lms CLI: {lms_check['stdout']}")
    else:
        print(f"❌ lms CLI 未安装或不在 PATH 中")
    
    # 检查 LM Studio API
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    lm_studio_running = sock.connect_ex(('127.0.0.1', 1234)) == 0
    sock.close()
    
    if lm_studio_running:
        print(f"✓ LM Studio API: 运行中 (http://localhost:1234)")
    else:
        print(f"❌ LM Studio API: 未运行")
    
    print(f"\n{'='*60}")
    print("诊断完成")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()

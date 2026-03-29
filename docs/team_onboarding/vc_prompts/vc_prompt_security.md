# VC引导：安全认证层

## 你的任务
构建系统的身份认证、权限管理和数据安全防护。

## 技术栈
- JWT (JSON Web Token) + Refresh Token机制
- bcrypt / Argon2 (密码哈希)
- OAuth 2.0 + OpenID Connect (第三方登录)
- Python + fastapi + python-jose + passlib

## 必须实现的功能

### 认证体系
- [ ] 用户注册/登录/登出API
- [ ] JWT访问令牌 (有效期: 15分钟)
- [ ] Refresh令牌 (有效期: 7天，Redis存储)
- [ ] 密码强度校验 (8位+大小写+数字+特殊字符)
- [ ] 登录失败限流 (5分钟内最多5次)

### 权限控制(RBAC)
- [ ] 角色定义: student, teacher, admin
- [ ] 权限装饰器: `@require_role("teacher")`
- [ ] 资源级权限 (用户只能访问自己的数据)
- [ ] API权限白名单/黑名单

### 安全防护
- [ ] SQL注入防护 (SQLAlchemy参数化)
- [ ] XSS攻击防护 (输入过滤+输出转义)
- [ ] CSRF Token验证
- [ ] 敏感操作二次确认 (修改密码/删除账号)

## 关键约束
⚠️ JWT密钥必须32位以上随机字符串，定期轮换
⚠️ 用户密码必须用bcrypt哈希，禁止明文存储
⚠️ 所有API必须认证后才能访问(登录/注册除外)
⚠️ 教师端数据必须严格隔离，防止越权访问

## 验收标准
- JWT无法被伪造/篡改
- 密码哈希无法被彩虹表破解
- 渗透测试无高危漏洞
- 接口响应包含正确CORS头

---

## Copilot引导关键词

```
"实现JWT访问令牌和刷新令牌机制"
"使用bcrypt对用户密码进行哈希存储"
"编写FastAPI权限装饰器@require_role"
"实现OAuth2授权码流程"
"配置CORS策略防止跨域攻击"
```

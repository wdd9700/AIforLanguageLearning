# 安全认证模块 - 对接集成指南

> **目标读者**: 其他模块开发者（成员A-G）  
> **目的**: 减少对接摩擦，提供"即插即用"的集成方案  
> **文档版本**: v1.0.0  
> **最后更新**: 2026-04-10

---

## 🚀 3分钟快速接入

### 步骤1：导入依赖

```python
from security_part.auth_routes import get_current_user
from security_part.rbac import Role, require_role, require_permission
```

### 步骤2：保护你的接口

```python
from fastapi import APIRouter, Depends

router = APIRouter()

# 基础认证 - 任何登录用户可访问
@router.get("/my-resource")
async def get_resource(current_user: dict = Depends(get_current_user)):
    return {"user": current_user["username"], "data": "..."}

# 角色控制 - 仅教师和管理员
@router.post("/grade-essay")
@require_role(Role.TEACHER)
async def grade_essay(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    return {"graded_by": current_user["username"]}

# 管理员专用
@router.delete("/system/config")
@require_role(Role.ADMIN)
async def delete_config(current_user: dict = Depends(get_current_user)):
    return {"deleted_by": current_user["username"]}
```

✅ **完成！** 你的接口现在已经受到保护。

---

## 📋 对接检查清单

### 接入前确认

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Redis已启动 | ☐ | Token存储依赖Redis，默认端口6379 |
| 环境变量配置 | ☐ | `JWT_SECRET_KEY` 必须设置 |
| 跨域配置 | ☐ | 前端域名需加入CORS白名单 |
| HTTPS启用 | ☐ | 生产环境必须启用，否则Cookie不安全 |

### 前端对接要点

```javascript
// 1. 登录后保存CSRF Token
const login = async (username, password) => {
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
    credentials: 'include'  // 关键：携带Cookie
  });
  const data = await res.json();
  // 保存CSRF Token到内存（不要存localStorage）
  window.csrfToken = data.data.csrf_token;
  return data;
};

// 2. 发送请求时携带CSRF Token
const apiCall = async (url, method = 'GET', body = null) => {
  const headers = {
    'Content-Type': 'application/json',
  };
  
  // POST/PUT/DELETE 需要CSRF Token
  if (method !== 'GET' && window.csrfToken) {
    headers['X-CSRF-Token'] = window.csrfToken;
  }
  
  return fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
    credentials: 'include'  // 关键：携带Cookie
  });
};

// 3. Token过期自动刷新
fetch('/api/something', { credentials: 'include' })
  .then(res => {
    if (res.status === 401) {
      // 尝试刷新Token
      return fetch('/auth/refresh', { 
        method: 'POST',
        credentials: 'include' 
      }).then(() => {
        // 重试原请求
        return fetch('/api/something', { credentials: 'include' });
      });
    }
    return res;
  });
```

---

## 🔌 各模块对接示例

### 成员A - 数据库/ES模块

**场景**: 需要验证用户身份后才能查询学习记录

```python
from security_part.auth_routes import get_current_user
from fastapi import Depends

@router.get("/learning-records")
async def get_records(
    current_user: dict = Depends(get_current_user)  # 自动验证身份
):
    # current_user 包含: username, role, email, is_active
    user_id = current_user["username"]
    
    # 查询该用户的学习记录（自动实现数据隔离）
    records = await db.query(
        "SELECT * FROM learning_logs WHERE user_id = ?", 
        user_id
    )
    return {"code": 200, "data": records}
```

**数据隔离原则**: 每个查询必须带上 `user_id` 过滤，严禁查询其他用户数据。

---

### 成员B - 基础设施模块

**场景**: 健康检查接口不需要认证，但管理接口需要

```python
from security_part.rbac import Role, require_role

# 公开接口 - 负载均衡器使用
@router.get("/health")
async def health_check():
    return {"status": "ok"}  # 无需认证

# 管理接口 - 仅管理员
@router.get("/admin/metrics")
@require_role(Role.ADMIN)
async def get_metrics(current_user: dict = Depends(get_current_user)):
    return {"cpu": "...", "memory": "..."}
```

---

### 成员C - 知识图谱模块

**场景**: 不同角色有不同的图谱访问权限

```python
from security_part.rbac import Role, require_permission

# 学生只能查看基础图谱
@router.get("/graph/basic")
@require_permission("graph:read:basic")
async def get_basic_graph(current_user: dict = Depends(get_current_user)):
    return await neo4j.query("MATCH (n:Basic) RETURN n")

# 教师可以查看完整图谱
@router.get("/graph/full")
@require_permission("graph:read:full")
async def get_full_graph(current_user: dict = Depends(get_current_user)):
    return await neo4j.query("MATCH (n) RETURN n")

# 管理员可以修改图谱
@router.post("/graph/nodes")
@require_permission("graph:write")
async def create_node(
    data: NodeData,
    current_user: dict = Depends(get_current_user)
):
    return await neo4j.create(data)
```

---

### 成员E - 模型路由模块

**场景**: 根据用户角色限制AI调用频率

```python
from security_part.rbac import Role

@router.post("/ai/chat")
async def ai_chat(
    message: str,
    current_user: dict = Depends(get_current_user)
):
    # 根据角色设置不同的限流策略
    role = current_user.get("role", Role.STUDENT.value)
    
    rate_limits = {
        Role.STUDENT.value: {"rpm": 10, "rpd": 100},   # 学生
        Role.TEACHER.value: {"rpm": 30, "rpd": 500},   # 教师
        Role.ADMIN.value: {"rpm": 100, "rpd": 10000},  # 管理员
    }
    
    limit = rate_limits.get(role, rate_limits[Role.STUDENT.value])
    
    # 检查限流
    if not await check_rate_limit(current_user["username"], limit):
        raise HTTPException(429, "Rate limit exceeded")
    
    # 调用AI模型
    response = await model_router.chat(message)
    return {"code": 200, "data": response}
```

---

### 成员F - 监控模块

**场景**: 记录用户操作日志，敏感操作告警

```python
from security_part.auth_routes import get_current_user
import logging

logger = logging.getLogger("audit")

@router.post("/sensitive-action")
async def sensitive_action(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    # 记录审计日志
    logger.info({
        "event": "sensitive_action",
        "user": current_user["username"],
        "role": current_user["role"],
        "ip": request.client.host,
        "action": "delete_resource",
        "resource_id": data.get("id")
    })
    
    # 执行操作
    result = await do_action(data)
    return result
```

---

### 成员G - 核心功能模块

**场景**: 词汇/作文/对话功能需要统一认证

```python
from security_part.rbac import Role, require_role
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1", dependencies=[Depends(get_current_user)])
# 注意：这里统一加了认证，该router下所有接口都需要登录

# 词汇功能 - 所有登录用户可用
@router.get("/vocabulary/list")
async def get_vocabulary():
    return {"words": [...]}

# 作文批改 - 仅教师
@router.post("/essay/grade")
@require_role(Role.TEACHER)
async def grade_essay(essay: EssayData):
    return {"score": 85, "comments": "..."}

# 对话练习 - 所有登录用户
@router.post("/conversation/chat")
async def chat(message: str):
    return {"reply": "..."}
```

---

## ⚠️ 常见对接问题

### 问题1：401 Unauthorized

**现象**: 接口返回 `{"detail": "Not authenticated"}`

**原因排查**:
1. 前端是否携带 `credentials: 'include'`?
2. Cookie是否被浏览器阻止（检查SameSite设置）?
3. Access Token是否过期？尝试调用 `/auth/refresh`
4. 后端是否正确配置了CORS?

**解决方案**:
```python
# main.py 中检查CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],  # 必须是具体域名，不能是*
    allow_credentials=True,  # 必须True才能携带Cookie
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 问题2：403 CSRF验证失败

**现象**: `{"detail": "CSRF token missing or invalid"}`

**原因**: POST/PUT/DELETE 请求没有携带 `X-CSRF-Token` 头

**解决方案**:
```javascript
// 确保从登录响应中获取CSRF Token
const csrfToken = loginResponse.data.csrf_token;

// 发送请求时添加Header
fetch('/api/something', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken,  // 必须！
  },
  credentials: 'include',
  body: JSON.stringify(data)
});
```

---

### 问题3：Redis连接失败

**现象**: Token刷新失败，或提示Redis错误

**原因**: Redis未启动或连接配置错误

**解决方案**:
```bash
# 启动Redis
docker run -d -p 6379:6379 redis:7-alpine

# 或设置环境变量使用远程Redis
export REDIS_URL="redis://username:password@host:6379/0"
```

**降级方案**: 如果Redis不可用，系统会自动回退到内存存储（仅单实例可用）。

---

### 问题4：权限控制不生效

**现象**: 普通用户能访问管理员接口

**原因**: 装饰器顺序错误或忘记添加

**正确写法**:
```python
@router.delete("/admin/users/{id}")
@require_role(Role.ADMIN)  # 先检查角色
async def delete_user(
    id: str,
    current_user: dict = Depends(get_current_user)  # 再获取用户信息
):
    pass
```

---

## 🔧 调试工具

### 快速测试认证流程

```bash
# 1. 注册
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Test1234!","email":"test@test.com"}'

# 2. 登录（保存Cookie）
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Test1234!"}' \
  -c cookies.txt -b cookies.txt

# 3. 访问受保护接口
curl http://localhost:8000/auth/me \
  -c cookies.txt -b cookies.txt

# 4. 带CSRF Token的POST请求
curl -X POST http://localhost:8000/api/something \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <从登录响应获取>" \
  -d '{"key":"value"}' \
  -c cookies.txt -b cookies.txt
```

### 检查Token状态

```python
# 在代码中调试
from security_part.redis_store import TokenStore
from security_part.auth_core import TokenService

# 检查Refresh Token是否存在
is_valid = TokenStore.validate_refresh_token("token_jti_here")
print(f"Token valid: {is_valid}")

# 解码Token查看内容
payload = TokenService.decode_token("access_token_here")
print(f"Token payload: {payload}")
```

---

## 📞 对接支持

遇到问题？按以下顺序寻求帮助：

1. **查看本文档** - 常见问题章节
2. **检查 HANDOVER.md** - 模块详细说明
3. **查看代码注释** - 每个函数都有详细docstring
4. **联系成员D** - 安全模块负责人

---

## 📝 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-04-10 | 初始版本，基础功能完成 |

---

**最后更新**: 2026年4月10日  
**维护者**: 成员D - 安全认证模块

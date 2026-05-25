# 接口测试用例：登录接口

## 接口信息

| 项目 | 内容 |
|------|------|
| 接口名称 | 用户登录 |
| 请求方法 | POST |
| 请求路径 | /api/login |
| Content-Type | application/json |
| 认证方式 | 无需认证（登录获取 Token） |

---

## 用例总览

| 用例编号 | 用例标题 | 测试维度 | 优先级 |
|----------|----------|----------|--------|
| API-LOGIN-001 | 正确账号密码登录成功 | 正常场景 | P0 |
| API-LOGIN-002 | 缺少 username 参数 | 参数异常 | P1 |
| API-LOGIN-003 | 缺少 password 参数 | 参数异常 | P1 |
| API-LOGIN-004 | username 为空字符串 | 参数异常 | P1 |
| API-LOGIN-005 | password 为空字符串 | 参数异常 | P1 |
| API-LOGIN-006 | username 超长（>32位） | 参数异常 | P2 |
| API-LOGIN-007 | password 超长（>20位） | 参数异常 | P2 |
| API-LOGIN-008 | username 含 SQL 注入字符 | 参数异常 | P1 |
| API-LOGIN-009 | password 含 XSS 字符 | 参数异常 | P1 |
| API-LOGIN-010 | 无 Token 访问需认证的接口 | 认证权限 | P0 |
| API-LOGIN-011 | 过期 Token 访问 | 认证权限 | P1 |
| API-LOGIN-012 | 连续错误密码触发锁定 | 业务逻辑 | P1 |
| API-LOGIN-013 | 锁定账号登录被拒 | 业务逻辑 | P1 |
| API-LOGIN-014 | 重复提交（幂等性） | 并发幂等 | P2 |

共 14 条用例（正常: 1 / 参数异常: 7 / 认证权限: 2 / 业务逻辑: 2 / 并发幂等: 1）

---

## 详细用例 + 请求/响应示例

### API-LOGIN-001 — 正确账号密码登录成功

```
POST /api/login
Content-Type: application/json

{
  "username": "testuser",
  "password": "Test@123"
}

预期响应 - 200:
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOi...",
    "expire_at": "2025-05-26T11:00:00Z",
    "username": "testuser"
  }
}
```

| 字段 | 内容 |
|------|------|
| 校验点 | code=200; data.token 非空; data.username 等于输入值 |

---

### API-LOGIN-002 — 缺少 username 参数

```
POST /api/login
Content-Type: application/json

{
  "password": "Test@123"
}

预期响应 - 400:
{
  "code": 400,
  "message": "参数错误：username 为必填项"
}
```

---

### API-LOGIN-008 — username 含 SQL 注入字符 | 安全检查

```
POST /api/login
Content-Type: application/json

{
  "username": "' OR '1'='1",
  "password": "anything"
}

预期响应 - 401:
{
  "code": 401,
  "message": "用户名或密码错误"
}
// 关键：不应返回数据库错误信息或异常堆栈
```

| 字段 | 内容 |
|------|------|
| 安全检查 | SQL注入 — 验证不返回数据库错误 |

---

### API-LOGIN-014 — 重复提交（幂等性）

```
# 第一次提交
POST /api/login
{"username": "testuser", "password": "Test@123"}
→ 200, 返回 Token A

# 第二次提交（相同参数，极短间隔）
POST /api/login
{"username": "testuser", "password": "Test@123"}
→ 200, 返回 Token B（新 Token，旧 Token A 应失效 或 返回相同 Token）

预期：两次都返回 200，第二次产生的 Token 可用且状态一致
```

---

## Postman Collection 导入建议

```
- Collection: 登录接口测试
  ├── Folder: 正常场景
  │   └── API-LOGIN-001 正确登录
  ├── Folder: 参数异常
  │   ├── API-LOGIN-002 缺username
  │   ├── API-LOGIN-003 缺password
  │   ├── API-LOGIN-004 username空
  │   ├── API-LOGIN-005 password空
  │   ├── API-LOGIN-006 username超长
  │   ├── API-LOGIN-007 password超长
  │   ├── API-LOGIN-008 SQL注入（安全）
  │   └── API-LOGIN-009 XSS（安全）
  ├── Folder: 认证权限
  │   ├── API-LOGIN-010 无Token
  │   └── API-LOGIN-011 Token过期
  ├── Folder: 业务逻辑
  │   ├── API-LOGIN-012 触发锁定
  │   └── API-LOGIN-013 锁定拒绝
  └── Folder: 并发幂等
      └── API-LOGIN-014 重复提交
```

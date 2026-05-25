# 缺陷报告示例

## 缺陷报告 BUG-20250525-001

### 基本信息

| 字段 | 内容 |
|------|------|
| Bug ID | BUG-20250525-001 |
| 标题 | [登录][正确密码]点击登录按钮后页面无响应，无任何提示 |
| 缺陷类型 | 功能缺陷 |
| 严重程度 | 严重（P1） |
| 优先级 | 高 |
| 发现版本 | v2.3.1 |
| 测试环境 | staging.example.com |

### 前置条件

- 系统可访问
- 存在已注册账号 testuser，密码 Test@123
- 账号未被锁定
- 验证码功能已关闭

### 复现步骤

1. 打开 staging.example.com/login
2. 输入用户名：testuser
3. 输入密码：Test@123
4. 点击「登录」按钮

### 实际结果

点击登录后按钮变灰，页面无跳转，无任何错误提示。等待 10 秒后按钮恢复可点击状态。打开浏览器开发者工具 Network 面板，发现 `/api/login` 请求一直处于 pending 状态，最终超时。

### 预期结果

- 登录成功后跳转到首页 `/dashboard`
- 顶部显示用户名 testuser
- 响应时间在 3 秒以内

### 复现频率

必现（5/5）

### 附件

- 截图：login-button-stuck.png（按钮灰色状态 + Network pending）
- 日志：截取前后 1 分钟的服务端日志，关键行标注 `@BUG-001`

### 根因推测

以下为推测，需开发确认：`/api/login` 接口可能在后端处理时发生死锁或外部依赖超时（如 Redis 连接池耗尽），导致请求挂起而非返回错误。

### 备注

- 关联用例：LOGIN-001
- 临时绕过方案：无，用户完全无法登录
- 影响范围：所有用户登录，功能完全阻断

---

## 好/差对比（同一 Bug 的不同写法）

| 维度 | ✗ 差 | ✓ 好 |
|------|-----|------|
| 标题 | "登录有问题" | "[登录][正确密码]点击登录按钮后页面无响应，无任何提示" |
| 复现步骤 | "登录系统，然后就出问题了" | "1. 打开 staging.example.com/login<br>2. 输入 testuser / Test@123<br>3. 点击登录" |
| 实际结果 | "登录失败" | "点击登录后按钮变灰，页面无跳转，无错误提示，10秒后恢复，Network 显示 /api/login pending 超时" |
| 预期结果 | "应该成功登录" | "登录成功后跳转 /dashboard，顶部显示用户名" |
| 测试数据 | "正确的账号密码" | "testuser / Test@123（已确认账号存在且未被锁定）" |

---

## 四类特殊场景示例

### 概率复现 Bug 示例

```
【复现概率增强信息】
- 已复现次数/尝试次数：3/10 = 30%
- 触发条件推测：并发场景下高概率触发，单用户操作时正常
- 当前发现规律：使用 JMeter 5 并发同时登录时，3/10 出现此问题
- 建议复现方式：用 JMeter 5 线程并发调用 /api/login
```

### 接口 Bug 示例

```
【接口请求/响应详情】
请求：
POST /api/login
Headers: Content-Type: application/json
Body: {"username": "testuser", "password": "Test@123"}

实际响应：（无响应，超时）
HTTP (pending → timeout)

正确响应应为：
HTTP 200
{"code": 200, "data": {"token": "eyJ...", "expire_at": "..."}}

是否可稳定复现：必现
```

### UI Bug 示例

```
【UI 环境信息】
- 设备/分辨率：iPhone 14 Pro / 393×852
- 浏览器：Safari 16.4
- 截图标注：见 login-button-cutoff.png（按钮右侧约 40% 被截断）
- 设计稿：Figma 链接 xxx
- 影响范围：仅 iOS Safari，Chrome/Android 正常
```

### Data Bug 示例

```
【数据详情】
- 数据来源：登录成功后自动写入 login_log 表
- 影响数据量：10 次登录中的 3 次
- 正确 vs 错误：
  正确：{"user_id": 123, "login_time": "2025-05-25 10:00:00", "status": "success"}
  错误：{"user_id": 123, "login_time": null, "status": "success"}
- 涉及表/字段：login_log.login_time
- 是否可修复：是，执行 UPDATE login_log SET login_time = created_at WHERE login_time IS NULL
```

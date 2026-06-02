# Audit Logging Design

本文档记录审计日志方案。这里的“审计日志”指平台管理行为记录，不包含任务内部执行日志，也不包含 Flask / Gunicorn / Celery 等应用运行日志。

## 设计结论

审计日志用于回答：

```text
谁在什么时候，对哪个租户下的什么资源，执行了什么管理操作，结果是什么？
```

审计日志应写入数据库，作为平台长期事实记录保存。

- 审计日志只记录平台管理行为。
- 审计日志不记录任务内部执行过程。
- 审计日志不替代应用运行日志。
- 审计日志默认永久保留。
- 审计日志原则上只追加，不修改、不删除。

## 与其他日志的边界

| 类型 | 关注点 | 存储建议 | 示例 |
| --- | --- | --- | --- |
| 应用运行日志 | 平台服务是否正常运行 | stdout / Docker logs / 文件 | Flask 异常、Gunicorn 启动、Celery worker 错误 |
| 审计日志 | 谁修改了平台资源 | 数据库表 | 创建租户、修改角色权限、禁用用户 |
| 任务日志 | 某个任务内部执行到了哪一步 | JSON Lines 文件 | CSV 解析开始、网页抓取失败 |

后续实现时，审计日志和任务日志应作为两个独立场景分别设计，不共用表结构或存储方案。

## 数据表建议

建议新增表：

```text
audit_logs
```

字段：

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| `id` | integer | 主键 |
| `tenant_id` | integer nullable | 操作所属租户；平台级操作为空 |
| `actor_user_id` | integer nullable | 操作者用户 ID |
| `actor_username` | string nullable | 操作者用户名快照 |
| `actor_is_superuser` | boolean | 操作者当时是否为平台超级管理员 |
| `action` | string | 操作码，例如 `role.update` |
| `resource_type` | string | 资源类型，例如 `role` / `user` / `tenant` |
| `resource_id` | string nullable | 资源 ID，使用字符串便于兼容非整数资源 |
| `resource_name` | string nullable | 资源名称快照 |
| `result` | string | `success` / `failure` |
| `before_data` | JSON nullable | 变更前数据 |
| `after_data` | JSON nullable | 变更后数据 |
| `metadata` | JSON nullable | 扩展上下文 |
| `ip_address` | string nullable | 请求 IP |
| `user_agent` | string nullable | 请求 User-Agent |
| `request_id` | string nullable | 请求追踪 ID，后续可补 |
| `created_at` | datetime | 创建时间 |

关键设计点：

- `tenant_id` 可为空，因为系统设置、超级管理员授权等操作属于平台级。
- `actor_username` 和 `resource_name` 存快照，避免后续改名后历史日志不可读。
- `resource_id` 建议使用字符串，便于记录系统设置 key 等非整数资源。
- `before_data` / `after_data` 只保存必要变更字段，不保存敏感数据。

## 操作码范围

第一版只覆盖高价值、会改变平台状态的管理操作。

| 模块 | 操作码 |
| --- | --- |
| 租户 | `tenant.create` / `tenant.update` / `tenant.delete` |
| 租户成员 | `tenant_member.add` / `tenant_member.remove` |
| 用户 | `user.create` / `user.update` / `user.delete` / `user.disable` / `user.enable` |
| 角色 | `role.create` / `role.update` / `role.delete` |
| 系统设置 | `system_setting.update` |
| 超级管理员 | `superuser.grant` / `superuser.revoke` |
| 安全操作 | `password.change` |

暂不要求记录所有 API 请求。审计日志关注业务语义明确的管理操作，而不是请求流水。

## 写入方式

审计日志应在 service 层显式记录，不建议通过全局 request hook 自动猜测。

原因：

- service 层最清楚业务语义。
- service 层可以拿到变更前后的数据。
- service 层可以记录资源名称快照。
- 全局 hook 难以判断具体 action 和 before / after 差异。

建议提供轻量审计日志服务：

```python
audit_log_service.record(
    action="role.update",
    resource_type="role",
    resource_id=str(role.id),
    resource_name=role.name,
    before_data=before,
    after_data=after,
    metadata={},
)
```

审计日志服务自动补充：

- 当前 `tenant_id`。
- 当前操作者 ID。
- 当前操作者用户名快照。
- 当前操作者是否为超级管理员。
- 请求 IP。
- User-Agent。
- 创建时间。
- 默认 `result="success"`。

## 成功与失败操作

第一版优先记录成功操作。

失败操作可以后续扩展，优先考虑：

- 登录失败。
- 越权访问。
- 删除受保护租户失败。
- 删除使用中的角色失败。
- 修改系统设置失败。

失败操作记录会涉及异常路径和错误码上下文，复杂度更高，第一版不强制覆盖所有失败场景。

## 查询权限

审计日志查询需要按身份控制可见范围。

| 用户类型 | 可见范围 |
| --- | --- |
| 平台超级管理员 | 可查看所有审计日志，可按租户筛选 |
| 租户管理员 | 只能查看当前租户审计日志 |
| 普通用户 | 默认不可查看 |

建议第一版提供统一查询接口：

```text
GET /api/v1/audit-logs
```

查询规则：

- 如果当前用户是 `is_superuser=true`，允许传 `tenant_id` 筛选。
- 如果当前用户不是超级管理员，只能查询当前 JWT 的 `tenant_id`。
- 租户管理员需要具备对应权限，例如 `system:audit`。

## 查询条件

第一版支持基础结构化查询即可。

建议支持：

- `tenant_id`
- `actor_user_id`
- `action`
- `resource_type`
- `resource_id`
- `result`
- `created_at` 起止时间
- 分页

第一版不做全文搜索。

## 数据保留

审计日志默认永久保留。

第一版不做：

- 自动清理。
- TTL。
- 删除审计日志接口。
- 归档策略。

如果未来日志量明显增长，应优先讨论归档，而不是直接删除历史审计日志。

## 安全规则

审计日志应避免记录敏感数据。

禁止或避免记录：

- 密码明文。
- token / cookie / secret。
- 完整请求头。
- 大段业务内容原文。

建议记录：

- 资源 ID。
- 资源名称快照。
- 修改字段。
- 变更前后的必要摘要。
- 操作者、租户、IP、User-Agent。

例如修改角色权限时，可以记录：

```json
{
  "before_data": {
    "name": "operator",
    "permissions": ["task:read"]
  },
  "after_data": {
    "name": "operator",
    "permissions": ["task:read", "task:create"]
  }
}
```

## 前端展示建议

第一版前端可以做一个简单审计日志页面：

- 表格展示时间、操作者、租户、动作、资源、结果。
- 支持按操作码、资源类型、操作者、时间范围筛选。
- 支持展开查看 `before_data`、`after_data`、`metadata`。

不需要第一版做复杂图表或全文检索。

## 当前不做

本阶段不引入：

- 平台运行日志系统。
- 任务执行日志。
- 全 API 请求流水记录。
- 自动清理。
- 归档。
- 全文搜索。
- 复杂合规报表。

## 后续实现原则

审计日志是平台管理行为的长期事实记录。新增管理类 service 时，如果会改变平台资源，应显式调用审计日志服务记录操作。

任务内部执行过程不要写入审计日志，应使用任务日志方案。

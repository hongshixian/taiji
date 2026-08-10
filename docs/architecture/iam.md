# Taiji IAM 拆分与迁移方案

> 状态：设计稿，等待开发授权  
> 目标版本：IAM V1  
> 最后更新：2026-08-10  
> 约束：本文只描述 `taiji` 仓库内的设计和后续实现，不涉及同级 `agent-iam` 仓库。

## 1. 目标

将太极现有的本地用户名密码认证拆分为独立运行的 Keycloak 身份服务，使太极和后续业务系统共享同一套全局账号、租户与成员关系，同时保留太极对自身业务权限和业务数据的管理权。

V1 需要满足：

- 用户只登录一次，不在登录时选择租户。
- 一个全局用户可以属于多个个人或企业租户。
- 太极 Header 展示用户在 IAM 中拥有的全部有效租户，并允许切换当前租户。
- 同一太极会话在任一时刻只有一个当前租户。
- 身份认证、全局用户、租户和成员关系由 Keycloak 管理。
- 太极继续定义任务、模型配置、Benchmark 等业务权限。
- 现有用户、租户、成员关系和业务数据可迁移且不改变本地业务主键。
- 旧的 `guest` 公共空间整体迁移为历史公共租户，不拆分其数据。

## 2. 最终架构

V1 不建设独立的 `agent-iam` 服务。Keycloak 是唯一 IAM 运行内核，IAM 定制代码与太极代码共同存放在 `taiji` 仓库，但以独立容器运行。

```text
Browser
  |
  | OIDC Authorization Code + PKCE
  v
Keycloak ---------------------------------------------------+
  |                                                         |
  | Java SPI / controlled REST / event listener             | NATS events
  v                                                         v
Taiji Backend (BFF)                                   NATS JetStream
  |                                                         |
  | Redis server session                                    +--> Taiji projector
  | tenant-local RBAC                                       +--> future systems
  v
Taiji PostgreSQL
```

### 2.1 Keycloak 负责

- 用户注册、登录、密码和账号恢复。
- 用户名、邮箱、显示名称与账号启停。
- OIDC/OAuth2 Client、Token 和 SSO 会话。
- 全局用户与 Organization。
- Organization 成员关系。
- `platform_admin`、`tenant_admin`、`member` 身份角色。
- 个人空间和企业租户的身份侧生命周期。
- 待注册邀请及邀请有效期。
- 向太极提供受控的 IAM REST API。
- 向 NATS 发布标准身份事件。

### 2.2 太极负责

- OIDC 回调和 Redis 服务端会话。
- 当前生效租户和上次使用租户。
- IAM 用户、租户和成员关系的本地投影。
- 太极业务权限码及两个固定角色的权限集合。
- 任务、模型配置、Benchmark、审计等业务数据。
- 所有按 `tenant_id` 执行的数据隔离。
- IAM 事件消费、按需落库和定期对账。

### 2.3 不再建设的组件

- 不运行独立 Go `agent-iam` 服务。
- 不创建 `agent-iam` 独立数据库。
- 不让浏览器直接调用 IAM 管理 API。
- 不让太极持有通用 Keycloak Admin API 权限。
- 不在太极保存或校验新用户密码。

## 3. 仓库规划

后续代码全部进入 `taiji` 仓库，建议新增：

```text
taiji/
├── iam/
│   ├── keycloak-extension/     # Java 21 + Maven，Keycloak SPI 与受控 REST API
│   ├── themes/                 # 登录、注册、账号中心主题
│   ├── realm/                  # Realm、Client、Role、Flow 的声明式配置
│   └── migration/              # 旧用户、租户、成员和凭据迁移工具
├── backend/                    # Flask BFF、本地投影、RBAC 与对账
├── frontend/                   # 登录跳转、租户切换和成员管理
└── docker/                     # Keycloak 与本地依赖镜像/配置
```

Keycloak 扩展必须锁定并测试具体 Keycloak 版本，升级 Keycloak 前必须先运行扩展兼容性测试。

## 4. IAM 领域模型

### 4.1 Realm

- 所有用户和租户使用一个统一业务 Realm。
- 不按租户拆 Realm。
- 用户是 Realm 全局用户，只创建一次。
- Organization 成员全部采用 unmanaged member，移出租户或停用租户不得删除全局账号。

### 4.2 稳定 ID

业务系统不得把 Keycloak 原生 `sub` 或 Organization ID 作为永久业务标识。Keycloak 扩展生成并维护只读的稳定 ID：

```text
User attribute:
  fc_global_user_id

Organization attribute:
  fc_global_tenant_id
```

规则：

- 使用 UUID，生成后不可修改。
- 通过 OIDC Protocol Mapper 和受控 REST API返回。
- 普通用户、租户管理员和业务系统均不能编辑。
- 太极以 `fc_global_user_id`、`fc_global_tenant_id` 建立本地投影。
- 未来更换 IAM 内核时原样导出和导入这两个 ID。
- Keycloak 原生 ID 仅作为当前 Provider 的技术映射和排障信息。

### 4.3 租户类型

```text
personal    个人空间
enterprise  企业租户，包括历史公共租户
```

Organization 使用以下受保护属性：

```text
fc_global_tenant_id
fc_tenant_type          personal | enterprise
fc_lifecycle_status     pending | active | disabled
fc_owner_user_id        仅个人空间使用
fc_protected            历史公共租户等保护对象
```

租户只能停用，产品和受控 API 永远不提供物理删除。Keycloak 基础设施管理员也不得通过日常运维流程删除业务 Organization。

### 4.4 固定角色

IAM 只保留三个身份角色：

```text
platform_admin  平台超级管理员，Realm 级
tenant_admin    租户管理员，Organization 级
member          标准成员，Organization 级
```

约束：

- 租户管理员和业务管理员是同一概念，不做区分。
- 企业租户允许多个 `tenant_admin`。
- 租户必须始终至少保留一名 `tenant_admin`。
- 管理员不能移除或降级最后一名管理员。
- 个人空间所有者固定为该空间的 `tenant_admin`。
- V1 不支持自定义角色。
- Keycloak 角色决定成员身份；具体太极权限码仍由太极本地代码定义。

## 5. 租户生命周期

### 5.1 个人空间

- 用户注册成功后自动创建一个个人 Organization。
- 固定名称为“`<username>` 的个人空间”。
- 用户名不可修改，因此个人空间名称稳定且不可修改。
- 个人空间只能有所有者本人，不能邀请其他成员。
- 所有者不能退出、被移除、停用成员关系或降级。
- 所有者拥有完整太极业务使用权限。
- 个人空间不能删除；用户停用后只归档并禁止访问。
- 创建流程必须幂等，重复注册事件、登录或对账不能创建第二个个人空间。

### 5.2 企业租户

- 仅 `platform_admin` 可以创建企业租户。
- 创建时必须指定初始租户管理员的完整用户名或邮箱。
- 初始管理员已经注册时，租户立即激活。
- 初始管理员尚未注册时，创建待注册邀请，租户保持 `pending`。
- `pending` 租户不能进入、不能添加普通成员。
- 初始管理员注册后自动成为 `tenant_admin`，随后激活租户。
- 租户管理员可以任命和撤销其他租户管理员，但必须保留最后一名管理员。
- 企业租户名称只能由 `platform_admin` 修改。
- 企业租户只能停用，不能删除。
- `platform_admin` 不自动成为企业租户成员，也不默认访问租户业务数据。

### 5.3 历史公共租户

现有 `guest` 租户整体迁移为一个受保护的 `enterprise` 租户：

- 保留现有租户本地 ID、业务数据和成员关系。
- 所有原 guest 成员继续保留成员身份。
- 原 `admin` 或 `is_owner=true` 成员迁移为 `tenant_admin`。
- 其他成员迁移为标准 `member`。
- 原自定义角色全部迁移为 `member`。
- 新注册用户不再自动加入历史公共租户。
- 历史公共租户不能删除。
- 每个旧用户还会额外获得自己的个人空间。
- guest 中的任务、模型配置和 Benchmark 配置不拆分、不复制到个人空间。

## 6. 成员与邀请

### 6.1 添加已注册用户

- 租户管理员只能使用完整用户名或完整邮箱精确查找。
- 不提供全局用户目录和模糊搜索。
- 匹配成功后可以直接加入企业租户，无需被邀请者同意。
- 加入后自动获得 `member`，除非明确任命为 `tenant_admin`。
- 操作必须通知目标用户并写入审计事件。

### 6.2 邀请未注册用户

- 完整邮箱查不到用户时可以创建待注册邀请。
- 邀请默认有效期 7 天，支持配置、撤销和重新发送。
- 用户注册后自动加入目标租户，不需要第二次确认。
- 初始管理员邀请会在注册后授予 `tenant_admin` 并激活租户。
- 普通邀请在注册后授予 `member`。

### 6.3 邮箱验证的 V1 决策

- V1 注册后不强制验证邮箱，可以立即使用个人空间。
- V1 未验证邮箱也会立即激活对应企业邀请。
- 这是已接受的阶段性安全风险：攻击者可能冒用被邀请邮箱注册并进入企业租户。
- 从 V1 开始即完整保留 `email_verified` 和“验证后激活邀请”的实现开关。
- 配置项建议为 `IAM_REQUIRE_EMAIL_VERIFICATION`，V1 默认 `false`。
- 正式扩大开放注册范围前应将其设为 `true`。

### 6.4 移除成员

- 移除实际执行为停用成员关系，不物理删除。
- 用户立即失去该租户访问权，相关太极会话回退个人空间。
- 历史任务、创建者信息和审计记录全部保留。
- 重新加入时恢复原成员记录并重新分配固定角色。
- IAM 全局用户不会因成员关系变化而删除。

## 7. 太极本地业务权限

Keycloak只返回 `tenant_admin` 或 `member`。太极后端把身份角色映射为本地固定权限集合，后端权限检查始终是最终防线。

### 7.1 tenant_admin

- 租户成员和租户管理员管理。
- 太极全部任务操作。
- 模型配置查看、新增、修改和删除。
- Benchmark 查看、使用、启用、停用和可达性检测。
- 太极租户审计日志查看。
- 其他租户级业务管理能力。

个人空间虽然映射为 `tenant_admin`，但个人空间类型约束优先，成员管理接口必须拒绝邀请、添加和移除操作。

### 7.2 member

- 查看租户内全部任务。
- 创建任务。
- 停止、重试和删除租户内任意成员创建的任务。
- 查看、新增、修改和删除租户内全部模型配置。
- 查看和使用已启用的 Benchmark。
- 不能启用、停用 Benchmark 或执行可达性管理。
- 不能管理成员、管理员和租户。
- 不能查看管理审计日志。

### 7.3 模型 API Key

- API Key 永远不可通过 API 读取明文。
- 接口只返回 `has_api_key` 和脱敏状态。
- 成员可以覆盖更新 Key，但无法取回已有值。
- 审计、日志、异常和 NATS 事件均不得包含 Key。

### 7.4 当前权限代码调整

- `user:*` 重命名为 `member:*`，避免与 IAM 全局用户管理混淆。
- 将任务权限语义统一为租户共享，不再描述为“只查看自己的任务”。
- 增加或调整任务管理权限，使 `member` 可以管理租户内全部任务。
- `member` 移除 `benchmark:write`。
- 删除租户自定义角色及对应管理界面/API。
- 保留权限码在太极代码侧硬编码、角色权限集合在太极侧定义的方式。

## 8. 登录与会话

### 8.1 登录页面

- 使用 Keycloak 托管的登录、注册、找回密码和 Account Console。
- 通过 Keycloak Theme 统一品牌样式。
- 太极不再渲染用户名密码表单。
- 太极账号设置页只提供跳转到 Keycloak Account Console 的入口。
- 用户可以使用用户名或邮箱登录。
- 用户名全局唯一且注册后不可修改。
- 邮箱和显示名称可以在 Account Console 修改。

### 8.2 OIDC 流程

- 使用 Authorization Code Flow。
- 启用 PKCE、`state` 和 `nonce` 校验。
- 登录时不让用户选择 Organization。
- 太极在登录完成后查询用户的全部 Organization，再在 Header 中选择当前租户。
- OIDC Token 和 IAM Refresh Token 只保存在太极服务端会话中，不进入浏览器存储。

### 8.3 BFF 会话

- Redis 保存服务端会话。
- 浏览器只保存随机 Session ID Cookie。
- Cookie 设置 `HttpOnly`、`Secure` 和合适的 `SameSite`。
- Cookie 认证的写请求必须启用 CSRF 防护。
- 空闲超时 2 小时，绝对最长 24 小时，均可配置。
- 当前租户按登录会话保存。
- 同一浏览器的标签页共享当前租户。
- 不同浏览器和设备的会话互不影响。
- 用户在太极退出时只清除太极本地会话，不退出 Keycloak SSO 和其他系统。

### 8.4 默认租户

- 用户首次登录默认进入个人空间。
- 后续登录优先恢复该会话或账号上次使用且仍有效的租户。
- 上次租户被停用或成员关系失效时回退个人空间。
- 切换租户必须实时验证有效 Organization membership。
- 切换只更新 Redis 会话，不重新签发太极 JWT。

### 8.5 IAM 暂时不可用

- 已登录用户可以在 5 分钟身份缓存窗口内继续使用普通业务功能。
- 登录、切换租户、成员管理和管理员操作必须失败关闭。
- 超过缓存窗口后所有受保护业务请求失败关闭。
- 缓存时间做成配置项。

## 9. Keycloak 受控扩展

扩展采用 Java 21 和与目标 Keycloak 版本一致的依赖，主要包含：

### 9.1 RealmResourceProvider

建议暴露版本化的受控 API，例如：

```text
GET    /realms/{realm}/taiji-iam/v1/me/tenants
GET    /realms/{realm}/taiji-iam/v1/tenants/{tenantId}/members
POST   /realms/{realm}/taiji-iam/v1/tenants
PATCH  /realms/{realm}/taiji-iam/v1/tenants/{tenantId}
POST   /realms/{realm}/taiji-iam/v1/tenants/{tenantId}/members
PATCH  /realms/{realm}/taiji-iam/v1/tenants/{tenantId}/members/{userId}
DELETE /realms/{realm}/taiji-iam/v1/tenants/{tenantId}/members/{userId}
POST   /realms/{realm}/taiji-iam/v1/invitations/{invitationId}/resend
DELETE /realms/{realm}/taiji-iam/v1/invitations/{invitationId}
```

要求：

- 用户发起的请求使用太极服务端保存的用户 Access Token，不能信任太极传入的 actor ID。
- 后台对账使用独立 Service Account 和最小权限 Client Credentials。
- 扩展内部校验 `platform_admin`、Organization 角色和租户类型。
- 永不暴露 Organization 删除接口。
- 所有写操作幂等，并接受客户端 `Idempotency-Key`。
- 错误响应包含稳定错误码，不向调用方泄露 Keycloak 内部异常。

### 9.2 EventListener SPI

- 处理注册、用户启停、资料变化、Organization 和 membership 变化。
- 注册后幂等创建个人空间并处理待注册邀请。
- Keycloak 事务提交成功后向 NATS JetStream 发布事件。
- 发布等待 JetStream 确认，失败时在进程内做有限重试。
- 不在 Keycloak 数据库增加自定义 Outbox 表，避免依赖不受支持的自定义 JPA API。
- NATS 事件不是唯一事实来源，业务系统必须定期对账。

### 9.3 Action Token 与邀请

- 使用 Keycloak Action Token/Required Action 能力承载邀请链接。
- 邀请 Token 必须单次使用、带租户和角色绑定并具有有效期。
- Token 内容不得允许客户端修改目标租户和角色。
- 邀请撤销后，即使旧链接未过期也必须拒绝。

### 9.4 Legacy Password SPI

- 迁移期只读访问旧太极用户凭据。
- 兼容验证现有 Werkzeug 密码哈希。
- 首次验证成功后将密码升级为 Keycloak 支持的格式并标记完成。
- 已完成迁移的用户不得再次查询旧凭据。
- 迁移窗口结束后移除 SPI、旧数据库凭据和网络访问。
- 不把明文密码发送给旧太极 HTTP 接口。

## 10. 本地投影与按需落库

### 10.1 User 投影

用户首次登录太极时创建或更新：

```text
users
  id                      保留太极本地主键
  iam_user_id             fc_global_user_id，唯一
  keycloak_subject        当前 Provider 技术 ID，仅排障
  username                显示缓存
  email                   显示缓存
  is_active               IAM 状态投影
  last_synced_at
```

迁移完成后删除或废弃：

- `password_hash`
- `tokens_revoked_at`
- 本地注册、改密和密码验证逻辑
- `is_superuser` 的权威含义；过渡期可保留为只读投影

### 10.2 Tenant 投影

用户第一次进入某个 IAM 租户时创建或更新：

```text
tenants
  id                      保留太极本地主键
  iam_tenant_id           fc_global_tenant_id，唯一
  keycloak_org_id         当前 Provider 技术 ID，仅排障
  slug                    太极本地稳定别名
  name                    IAM 显示名称缓存
  tenant_type             personal | enterprise
  lifecycle_status        pending | active | disabled
  is_protected
  last_synced_at
```

Header 可以先展示 IAM 返回但尚未在太极落库的租户。用户选择时，太极验证 membership 并幂等创建本地投影。

### 10.3 Membership 投影

```text
tenant_memberships
  id
  user_id
  tenant_id
  iam_role                tenant_admin | member
  is_active
  is_owner
  sync_version
  last_synced_at
```

保留 `(user_id, tenant_id)` 唯一约束。Keycloak 是成员关系和身份角色事实来源，太极表用于高效授权、查询和历史关联。

## 11. 事件与对账

### 11.1 NATS

- NATS JetStream 是独立平台基础设施，不属于 Keycloak 内部组件。
- 开发环境可以随太极 Compose 启动单节点。
- 生产环境使用独立持久化集群。
- Keycloak 是生产者，太极和后续系统使用独立 durable consumer。

建议 Subject：

```text
iam.user.created.v1
iam.user.updated.v1
iam.user.disabled.v1
iam.tenant.created.v1
iam.tenant.updated.v1
iam.tenant.disabled.v1
iam.membership.created.v1
iam.membership.updated.v1
iam.membership.disabled.v1
iam.invitation.created.v1
iam.invitation.expired.v1
```

统一事件信封：

```json
{
  "event_id": "uuid",
  "event_type": "iam.membership.updated.v1",
  "occurred_at": "2026-08-10T12:00:00Z",
  "realm": "fangcun",
  "aggregate_id": "stable-global-id",
  "aggregate_version": 3,
  "data": {}
}
```

要求：

- 不发布密码、Token、API Key 等秘密。
- 尽量减少邮箱等个人信息，消费者需要详情时通过受控 API 获取。
- 消费者按 `event_id` 幂等。
- 对同一 aggregate 使用稳定消息键，尽量保持顺序。
- 事件版本不做破坏性修改，新结构使用新版本 Subject。

### 11.2 对账

因为不建设独立 Outbox Relay，必须把对账作为正式能力：

- 用户登录时对账当前用户、租户列表和角色。
- 切换租户时实时对账目标 membership。
- 成员管理前实时读取 Keycloak 状态。
- 太极后台周期性对账已落库的活跃租户和成员。
- 建议每 5 分钟增量对账、每日一次全量一致性检查。
- 对账只修复投影，不覆盖太极业务数据。
- 不一致和修复结果写入审计与指标。

## 12. 多租户安全加固

保留现有 `TenantMixin` 和 SQLAlchemy 查询拦截，但需要补齐：

- 所有受保护业务请求在数据库访问前必须得到有效 `g.tenant_id`。
- 缺少租户上下文时失败关闭，不能因为 `g.tenant_id=None` 变成无过滤查询。
- 增加写入校验，阻止创建或修改其他租户的 `TenantMixin` 对象。
- Celery 任务显式携带并验证 `tenant_id`。
- `bypass_tenant_filter` 只允许内部对账、迁移和超级管理员受控路径。
- 平台超级管理员没有 membership 时不能读取租户业务数据。
- 租户切换后页面数据和缓存必须整体失效或按租户分区。
- 后端授权为最终权威，前端路由权限仅用于界面控制。

## 13. 管理员与安全策略

### 13.1 首个平台超级管理员

旧数据迁移：

- 现有 `admin` 用户迁入 Keycloak。
- 保留用户名 `admin`。
- 授予 `platform_admin`。
- 不复制已公开的固定密码。

全新生产部署：

- 仅在空 IAM 数据库且未完成 Bootstrap 时创建固定用户名 `admin`。
- 系统使用密码学安全随机源生成高强度一次性密码。
- 一次性密码只在 Bootstrap 流程中展示一次，不写普通应用日志。
- Keycloak 将密码标记为 temporary，首次登录必须修改。
- 初始化成功后写入完成标记，服务重启不能重复创建或重新授权。
- 管理员恢复必须执行专用恢复命令。
- 普通注册禁止占用保留用户名 `admin`。

### 13.2 MFA

- V1 不强制启用 MFA。
- Keycloak 保留 TOTP 和 Passkey 能力。
- V1 管理员仍必须满足强密码、登录限流和异常审计。
- 后续可以通过 Required Action 和 Realm 策略逐步强制管理员 MFA。

### 13.3 Keycloak 管理面

- Keycloak 基础设施管理员与业务 `platform_admin` 分离。
- Admin Console 仅允许运维网络访问。
- 日常租户和成员操作只能走受控 REST API。
- 业务系统不能获得 Realm 全量管理权限。
- 所有敏感配置来自 Secret，不提交到 Git。

## 14. 旧数据迁移

### 14.1 原则

- 先增加兼容字段，再回填，再切换读取，最后删除旧字段。
- 保留太极本地用户、租户、任务和其他业务主键。
- 所有迁移步骤幂等、可重跑，并记录成功、失败和重试状态。
- 单用户或单租户独立事务，避免一次失败回滚全部数据。
- 迁移前完整备份数据库和任务文件。

### 14.2 用户

1. 为每个旧用户生成 `fc_global_user_id`。
2. 导入 Keycloak 用户名、邮箱、显示名称和启停状态。
3. 当前 `is_superuser=true` 的有效管理员映射为 `platform_admin`，并重点人工复核。
4. 不直接复制不兼容的密码哈希到 Keycloak 内置凭据表。
5. Legacy Password SPI 在首次登录时验证旧哈希并升级凭据。
6. 迁移完成后回填太极 `users.iam_user_id`。

### 14.3 租户与成员

1. 为每个现有租户创建 Keycloak Organization 和 `fc_global_tenant_id`。
2. 现有 guest 转换为受保护的历史公共企业租户。
3. 原 `admin` 或 owner 映射 `tenant_admin`，其他映射 `member`。
4. 现有自定义角色全部映射为 `member`。
5. 为每个旧用户创建个人 Organization 和 owner membership。
6. 回填太极 `iam_tenant_id`、`keycloak_org_id` 和固定角色。
7. 不移动历史公共租户的业务数据。

### 14.4 认证切换

1. 先部署 Keycloak、扩展、Realm 配置和 NATS。
2. 导入用户和租户，但暂不改前端登录入口。
3. 在测试环境完成旧密码首次登录迁移验证。
4. 太极增加 OIDC/BFF 会话并通过功能开关灰度。
5. 切换前端登录、注册、登出和账号设置。
6. 保留短期回滚开关，但不允许新旧认证同时长期运行。
7. 迁移窗口结束后删除本地注册、改密、JWT 刷新和密码验证入口。
8. 移除 Legacy Password SPI 的旧库权限后再删除旧密码字段。

### 14.5 回滚

- 数据库迁移在删除旧字段前均可回滚应用版本。
- Keycloak 导入和 Organization 创建为幂等操作，不因回滚删除。
- 灰度期出现问题时恢复旧登录入口，保留已生成的稳定 ID。
- 一旦删除旧密码字段和 Legacy SPI，认证回滚仅能通过 Keycloak 完成，不再回到本地密码。

## 15. 前端改造

- 删除本地登录和注册表单，改为跳转 Keycloak。
- `auth` store 不再读写 `accessToken`、`refreshToken` 和 `originalTenantId`。
- Axios 设置 `withCredentials=true`，不再附带 Bearer Token。
- 401 进入太极登录跳转流程，不在前端刷新 IAM Token。
- `/auth/me` 作为会话和当前权限的唯一前端来源。
- 保留现有 TenantSwitcher 交互，数据源改为 IAM 租户列表。
- 租户选项明确标识个人空间和企业租户。
- 用户管理页改为成员管理页，不再输入或修改密码。
- 成员添加只接受完整用户名或邮箱。
- 删除操作改名为“移出租户”，后端执行 membership 停用。
- 删除自定义角色管理页面或改成两个固定角色的只读说明。
- 账号设置跳转 Keycloak Account Console。

## 16. 后端接口调整

太极建议保留兼容的前端 API 形态：

```text
GET  /api/v1/auth/login             跳转 Keycloak
GET  /api/v1/auth/callback          OIDC 回调并创建太极会话
POST /api/v1/auth/logout            只清除太极会话
GET  /api/v1/auth/me                当前用户、租户、角色和权限
GET  /api/v1/auth/tenants           用户全部有效租户
POST /api/v1/auth/switch-tenant     切换 Redis 会话当前租户
```

移除或废弃：

```text
POST /api/v1/auth/register
POST /api/v1/auth/login             旧用户名密码 JSON 登录
POST /api/v1/auth/refresh
PUT  /api/v1/auth/password
```

成员管理接口只操作 Keycloak 受控 API 和太极投影，不允许修改全局用户名、邮箱、密码或账号启停状态。

## 17. 测试与验收

### 17.1 Keycloak 扩展

- 个人空间创建幂等。
- 个人空间禁止添加成员、移除 owner 和降级 owner。
- 企业租户初始管理员已注册和未注册两条流程。
- 邀请过期、撤销、重发和重复注册事件。
- 最后一名租户管理员保护。
- `platform_admin` 不自动获得租户业务访问权。
- 租户停用但不删除。
- 受控 REST API 越权和 IDOR 测试。
- NATS 事件结构、重试和去重测试。
- Legacy Password SPI 对现有哈希样本的兼容测试。

### 17.2 太极

- OIDC `state`、`nonce`、PKCE 和回调错误处理。
- Cookie、CSRF、会话固定攻击和退出测试。
- 首次登录创建本地 User 与个人 Tenant 投影。
- IAM 租户尚未落库时的 Header 展示和首次切换。
- 当前租户按会话隔离，不同会话互不影响。
- 被移除、用户停用和租户停用后的立即失效。
- IAM 故障 5 分钟缓存和敏感操作失败关闭。
- `member` 与 `tenant_admin` 的固定权限矩阵。
- 所有业务模型跨租户读取和写入隔离。
- NATS 重复、乱序和漏事件后的对账修复。
- 历史公共租户成员和数据完整性。

### 17.3 迁移

- 生产数据副本上的全量演练。
- 用户、租户、成员、角色数量迁移前后核对。
- 每个用户恰好一个个人空间。
- 历史公共租户无数据移动或丢失。
- 旧 admin 获得 `platform_admin` 且固定旧密码不可用。
- 已迁移密码用户不再访问旧凭据。
- 可重复运行迁移而不产生重复用户、Organization 或 membership。

## 18. 实施阶段

### Phase 1：基础设施与扩展骨架

- Keycloak 和独立数据库初始化。
- 单 Realm、Client、Role 和 Theme。
- Java 扩展工程、受控 REST API 骨架和测试环境。
- NATS JetStream 开发环境。

### Phase 2：IAM 领域能力

- 稳定 ID。
- 个人空间。
- 企业租户、固定角色、成员和邀请。
- 租户停用、最后管理员保护和 Bootstrap admin。
- NATS Event Listener。

### Phase 3：太极 BFF 与本地投影

- OIDC 回调、Redis 会话和 CSRF。
- User、Tenant、Membership 兼容字段和投影服务。
- `/me`、租户列表和租户切换。
- 权限装饰器改为读取服务端当前 membership。
- 查询和写入租户隔离加固。

### Phase 4：迁移与前端

- Legacy Password SPI 和数据迁移工具。
- 历史公共租户及个人空间回填。
- 前端登录、账号设置、TenantSwitcher 和成员管理改造。
- 固定角色权限调整。

### Phase 5：灰度与清理

- 生产数据演练和回滚演练。
- 小范围灰度 OIDC。
- 监控事件、对账、会话和权限错误。
- 完成切换后移除本地密码、JWT 和自定义角色代码。
- 移除 Legacy Password SPI 和旧数据库访问权限。

## 19. 开发前门禁

在获得明确开发授权前，不执行以下操作：

- 不新增 Keycloak、NATS 或数据库运行组件。
- 不修改太极认证和权限代码。
- 不创建数据库迁移。
- 不修改前端登录与租户切换。
- 不导入或变更任何真实用户数据。

开始开发前至少需要确认：

- 本文作为 IAM V1 基线方案获得批准。
- 目标 Keycloak 版本和镜像来源确定。
- 开发、测试环境的域名与回调地址确定。
- PostgreSQL、Redis、NATS 的开发环境资源可用。
- 旧数据迁移使用生产脱敏副本完成演练。
- 已准备测试邮箱和非生产 SMTP。

## 20. 已知 V1 风险

- 邮箱未验证即可激活企业邀请，存在邮箱冒用风险；已经通过配置开关预留修复路径。
- V1 不强制管理员 MFA，高权限账号仍依赖密码安全。
- Keycloak 自定义 Java SPI 增加升级测试成本。
- 直接发布 NATS 不具备严格事务 Outbox 保证，必须依靠对账修复漏事件。
- 取消独立 IAM 适配层后，太极会依赖 Keycloak 受控 API；未来更换 IAM 需要替换此集成。
- 固定双角色降低复杂度，但无法表达企业内更细的职责划分。

这些风险在 V1 中接受，但必须进入发布检查表和后续安全迭代计划。

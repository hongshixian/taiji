# Task Logging Design

本文档记录任务日志方案。这里的“任务日志”只指任务内部执行过程日志，不包含平台系统日志 / 审计日志。

## 设计结论

平台提供任务日志基础设施，任务按需调用该能力写执行事件。

- 平台负责：日志存储、路径生成、JSONL 格式、文件读写、读取权限校验。
- 任务负责：决定是否写日志、在哪些步骤写日志、日志事件名和业务上下文。
- 数据库负责：保存任务状态、任务结果摘要、错误摘要，以及任务日志入口元信息。

任务日志是可选能力。新任务只要维护好 `tasks` 主记录和自己的详情表，就可以完全不使用任务日志。

## 与平台审计日志的边界

任务日志和平台审计日志是两个不同场景，不共用一套设计。

| 类型 | 关注点 | 存储建议 | 示例 |
| --- | --- | --- | --- |
| 平台审计日志 | 谁在什么时候修改了平台资源 | 独立数据库表，后续单独设计 | 创建租户、修改角色、调整系统设置 |
| 任务日志 | 某个任务内部执行到了哪一步 | JSON Lines 文件 | CSV 解析开始、网页抓取失败、任务执行完成 |

任务状态不属于任务日志。`tasks.status`、`started_at`、`completed_at`、`error_message` 等平台管理字段继续保存在数据库中。

## 文件存储方案

当前部署假设是单机 Docker Compose。backend 和 worker 共享同一个持久化日志目录。

宿主机目录：

```text
./app_logs
```

容器内目录：

```text
/app/logs
```

日志文件结构：

```text
app_logs/
└── tasks/
    └── tenant_10/
        ├── webpage_analysis/
        │   ├── task_10001.jsonl
        │   └── task_10002.jsonl
        └── csv_quality/
            ├── task_10003.jsonl
            └── task_10004.jsonl
```

路径规则：

```text
tasks/tenant_{tenant_id}/{task_type}/task_{task_id}.jsonl
```

示例：

```text
tasks/tenant_10/csv_quality/task_10003.jsonl
```

数据库保存相对路径，不保存 `/app/logs/...` 这样的绝对路径。

## Docker Compose 约定

backend 和 worker 挂载同一个日志目录：

```yaml
services:
  backend:
    environment:
      - TASK_LOG_ROOT=/app/logs
    volumes:
      - ./app_data:/app/data
      - ./app_logs:/app/logs

  worker:
    environment:
      - TASK_LOG_ROOT=/app/logs
    volumes:
      - ./app_data:/app/data
      - ./app_logs:/app/logs
```

本地开发可通过环境变量覆盖日志根目录，例如：

```bash
TASK_LOG_ROOT=../app_logs
```

## 数据库元信息

数据库不保存任务日志明细，只保存日志入口。

建议在 `tasks` 主表增加字段：

```text
log_path VARCHAR(500) NULL
```

`log_path` 保存相对路径，例如：

```text
tasks/tenant_10/csv_quality/task_10003.jsonl
```

`log_path` 可以为空。为空表示该任务没有使用平台任务日志能力，前端展示“暂无执行日志”。

## JSON Lines 格式

每行是一条独立 JSON，不使用 JSON 数组。

示例：

```jsonl
{"ts":"2026-06-01T14:30:01.123Z","level":"INFO","step":"fetch","event":"fetch_started","msg":"开始抓取网页","elapsed_ms":0,"data":{}}
{"ts":"2026-06-01T14:30:02.456Z","level":"WARN","step":"fetch","event":"fetch_retry","msg":"请求超时，重试第1次","elapsed_ms":1500,"data":{"retry":1}}
{"ts":"2026-06-01T14:30:05.789Z","level":"INFO","step":"fetch","event":"fetch_finished","msg":"抓取成功","elapsed_ms":4500,"data":{"status_code":200}}
```

统一字段：

| 字段 | 说明 |
| --- | --- |
| `ts` | UTC ISO 时间戳 |
| `level` | `DEBUG` / `INFO` / `WARN` / `ERROR` |
| `step` | 当前执行阶段 |
| `event` | 机器可读事件名 |
| `msg` | 人类可读消息 |
| `elapsed_ms` | 距任务日志创建时间经过的毫秒数 |
| `data` | 结构化上下文，默认 `{}` |

`msg` 用于展示，`event` 用于筛选和机器处理，`data` 用于保存业务上下文。

## 平台日志服务职责

平台应提供一个轻量任务日志服务。任务通过该服务写日志，而不是直接拼路径或操作文件。

平台日志服务负责：

- 根据 `tenant_id`、`task_type`、`task_id` 生成相对日志路径。
- 基于 `TASK_LOG_ROOT` 生成实际文件路径。
- 创建日志目录。
- 以追加方式写入 JSONL。
- 自动补充 `ts`、`level`、`elapsed_ms` 等统一字段。
- 读取日志文件并按行解析。
- 做路径安全校验，防止路径穿越。
- 隐藏本地文件存储细节，为后续迁移到对象存储预留空间。

平台日志服务不负责：

- 不决定任务状态。
- 不决定任务执行流程。
- 不决定任务业务步骤。
- 不强制每个任务写日志。
- 不解析任务日志里的业务含义。
- 不替代平台审计日志。

概念调用方式：

```python
logger = create_task_logger(
    tenant_id=10,
    task_type="csv_quality",
    task_id=10003,
)

logger.info(step="parse", event="csv_parse_started", msg="开始解析 CSV")
logger.warn(
    step="validate",
    event="missing_values_found",
    msg="发现缺失值",
    data={"rows": 12},
)
logger.error(
    step="execute",
    event="task_failed",
    msg="任务执行失败",
    data={"error": "timeout"},
)
```

## 读取规则

前端读取任务日志时，不能让前端传文件路径。

推荐 API 形态：

```text
GET /api/v1/tasks/<task_id>/logs
```

后端读取流程：

1. 根据当前 JWT 的 `tenant_id` 查询 `tasks`。
2. 确认任务属于当前租户。
3. 读取该任务的 `log_path`。
4. 将 `TASK_LOG_ROOT` 与 `log_path` 拼接为实际路径。
5. 校验最终路径仍在 `TASK_LOG_ROOT` 内。
6. 按行读取 JSONL 并解析。
7. 返回日志数组或分页结果。

如果 `log_path` 为空或文件不存在，返回空日志列表即可。

## 安全规则

任务日志不应记录敏感原文。

禁止或避免记录：

- 完整 CSV 内容。
- token、cookie、密钥、密码。
- 完整网页响应正文。
- 带敏感参数的完整请求头。

允许记录：

- 文件名。
- 行数、列数、列名。
- 错误行号和错误类型。
- URL 域名或必要的目标 URL。
- 外部请求状态码。
- 任务执行耗时和重试次数。

错误堆栈可以适度保留，但应避免包含敏感参数。

## 当前不做

本阶段不引入：

- 数据库任务日志明细表。
- Loki / ELK / OpenTelemetry。
- Redis Stream。
- 对象存储。
- 跨机器 worker 共享日志。
- 复杂归档和全文检索。
- 按时间分目录。

如果后续单租户单任务类型下文件数量明显增长，再考虑基于任务 ID 分片，例如：

```text
tasks/tenant_10/csv_quality/10000/task_10001.jsonl
```

## 后续实现原则

新增任务接入任务日志时，只依赖轻量日志接口：

```text
log(level, step, event, msg, data)
```

任务不应知道日志根目录、文件路径生成规则、JSONL 序列化方式和读取 API。

不需要执行日志的任务可以完全不调用平台日志服务，`tasks.log_path` 保持为空。

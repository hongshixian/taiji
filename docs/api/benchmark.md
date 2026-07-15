# Benchmark 测评 API

任务管理下「Benchmark 测评」模块的前后端交互接口约定。

- 所有接口统一前缀 `/api/v1`，由前端 `src/api/request.ts` 的 `baseURL` 注入。
- 鉴权：除登录外均需 `Authorization: Bearer <jwt>`，并要求对应权限（见各接口「权限」）。
- 统一响应 envelope：`{ "code": 0, "message": "...", "data": ... }`；`code=0` 成功，非 0 为业务错误。分页响应的 `data` 形如 `{ items, total, page, per_page, pages }`。
- 多租户：所有查询自动限定在当前租户（JWT 解析出的 `tenant_id`），前端无需传租户参数。

> 本文档随 API 变动同步更新。新增 / 修改接口后请回来修订对应小节。

---

## 1. 元数据接口（引擎无关）

挂在 `/api/v1/benchmarks` 下，供前端新建任务对话框的 dynamic form 使用。

### 1.1 获取全部测评集

`GET /benchmarks/suites`

- 权限：`task:read`
- 返回当前引擎注册的全部 `SuiteDescriptor`（含已禁用项，前端按 `disabled` 过滤展示）。

响应 `data`：

```jsonc
{
  "items": [
    {
      "key": "mmlu",                 // 平台内部唯一 key（提交时用）
      "engine": "inspect_evals",
      "display_name": "MMLU",
      "category": "capability",       // capability / safety / alignment
      "description": "...",
      "needs_judge": false,           // 是否需要评委模型
      "needs_sandbox": false,
      "default_config": {},           // 含 execution 默认值等
      "config_schema": { "fields": [ /* DynamicField 定义 */ ] },
      "disabled": false,
      "disabled_reason": null,
      "notes": null                   // 前端 tooltip
    }
  ],
  "total": 36
}
```

### 1.2 获取执行配置字段声明

`GET /benchmarks/execution-schema`

- 权限：`task:read`
- 返回 `execution_config` 各字段的 schema（供前端表单渲染）。

---

## 2. 任务生命周期接口

挂在 `/api/v1/tasks/benchmark` 下，由 `BenchmarkHandler`（继承 `BaseTaskHandler`）自动生成标准路由 + benchmark 特有路由。

### 2.1 提交任务

`POST /tasks/benchmark/`

- 权限：`task:create`
- 限流：`20 per minute`
- 请求体（`BenchmarkSubmitSchema`）：

```jsonc
{
  "task_name": "gpt-4o-mmlu-20260715-1030",  // 必填，1-100 字，非空白；前端可为空时自动生成
  "notes": null,                              // 可选，≤500 字
  "benchmark_suite": "mmlu",                  // 必填，必须为已启用 suite key
  "target_model_id": 1,                       // 必填，被测模型 id
  "judge_model_id": 2,                        // needs_judge=true 时必填
  "execution_config": {                       // 引擎无关执行控制
    "limit": 20,                              // 样本数；null=全集
    "max_connections": 10,
    "epochs": 1,
    "timeout_minutes": 60
  },
  "suite_config": {}                          // suite 特有参数（DynamicField 提交的 KV）
}
```

- 响应 `data`：`BenchmarkTask`（见 §4.1），HTTP 201。
- 提交后由后端 `delay` Celery 任务异步执行。

### 2.2 分页查询任务列表

`GET /tasks/benchmark/?page=1&per_page=10`

- 权限：`task:read`
- query：`page`（≥1，默认 1）、`per_page`（1-100，默认 20）。
- 响应 `data`：分页结构，`items` 为 `BenchmarkTask[]`。
- ⚠️ 列表项的 `result.samples_preview` **恒为空数组**（预览文本不再随结果存储），仅保留 `sample_grid` 状态网格；样本预览文本按需通过 §2.7 拉取。

### 2.3 任务状态统计【指标用】

`GET /tasks/benchmark/stats`

- 权限：`task:read`
- 返回当前租户 benchmark 任务按状态的全局计数（不依赖分页），供页面顶部「进行中 / 累计任务」指标使用。
- 响应 `data`：

```jsonc
{
  "pending": 1,
  "running": 2,
  "success": 30,
  "failed": 2,
  "stopped": 1,
  "active": 3,    // pending + running
  "total": 36     // 全部状态之和
}
```

> 前端每 2s 轮询此接口刷新指标，保证「进行中」随全局状态近实时变化（不再只反映当前分页）。

### 2.4 获取任务详情

`GET /tasks/benchmark/<task_id>`

- 权限：`task:read`
- 响应 `data`：`BenchmarkTask`（含 `result`，但 `samples_preview` 同样为空，见 §2.2 说明）。
- 前端用于展开行渲染结果卡片 + 轮询进行中任务的进度。

### 2.5 重试任务

`POST /tasks/benchmark/<task_id>/retry`

- 权限：`task:create`
- 清空 `result` 与 `progress`，重置为 `pending` 并重新派发 Celery 任务。
- 响应 `data`：重置后的 `BenchmarkTask`。

### 2.6 停止任务

`POST /tasks/benchmark/<task_id>/stop`

- 权限：`task:create`
- 仅 `pending` / `running` 可停止。`pending` 撤销队列任务；`running` 终止执行进程（SIGTERM）。
- 响应 `data`：状态置为 `stopped` 的 `BenchmarkTask`。

### 2.7 获取单条样本预览【懒加载】

`GET /tasks/benchmark/<task_id>/samples/<sample_id>`

- 权限：`task:read`
- `sample_id` 为路径段（字符串匹配，如 `5` 或 `abc`）。
- 按需从 `result.artifact_paths` 指向的 `.eval` log 中读取对应样本的预览文本（实时解析，无条数上限）。
- 响应 `data`（命中时）：

```jsonc
{
  "id": 5,
  "input": "...",        // 已截断至 500 字
  "target": "...",
  "output": "...",
  "score": "C",
  "explanation": "...",  // 可空
  "error": null          // 执行报错时非空
}
```

- 未命中（样本不存在 / `.eval` log 缺失）：`code=90404`，message「该样本暂无预览数据（可能超出预览范围，请查看完整日志）」，前端据此提示跳转完整日志。

> 设计：列表/详情接口只回传 `sample_grid`（每样本仅 `{id, status}`，紧凑）；预览文本不随结果存储（避免大 N 撑大 result JSON），点击方块时才按需读取 `.eval` log 解析对应样本。

### 2.8 删除任务

`DELETE /tasks/benchmark/<task_id>`

- 权限：`task:delete:any`（管理员）
- 级联删除详情记录与产物关联。响应仅 `message`。

---

## 3. 任务日志接口（通用）

### 3.1 获取执行日志

`GET /tasks/<task_id>/logs`

- 权限：`task:read`
- 挂在通用 `task_bp`（`/api/v1/tasks`）下，benchmark / red_team 共用。
- 响应 `data`：

```jsonc
{
  "task_id": 10,
  "task_type": "benchmark",
  "log_path": "/data/logs/.../task_10.jsonl",
  "items": [
    { "ts": "2026-07-15T10:00:00Z", "level": "info", "step": "run", "event": "engine_started", "msg": "...", "elapsed_ms": 0, "data": {} }
  ]
}
```

---

## 4. 数据结构

### 4.1 BenchmarkTask

```jsonc
{
  "id": 10,
  "task_type": "benchmark",
  "task_type_name": "Benchmark 测评",
  "status": "success",            // pending / running / success / failed / stopped
  "error_message": null,
  "log_path": "...",
  "user_id": 1,
  "username": "admin",
  "created_at": "2026-07-15T10:00:00Z",
  "started_at": "2026-07-15T10:00:01Z",
  "completed_at": "2026-07-15T10:05:30Z",
  // benchmark 详情
  "task_name": "gpt-4o-mmlu-...",
  "notes": null,
  "engine": "inspect_evals",
  "benchmark_suite": "mmlu",
  "target_model_id": 1,
  "judge_model_id": null,
  "target_model": { /* ModelConfig，已剔除 api_key */ },
  "judge_model": null,
  "benchmark_config": { "execution_config": {}, "suite_config": {} },
  "progress": { "completed": 20, "total": 20, "current_metrics": {}, "sample_grid": [{ "id": 1, "status": "success" }] },  // 进行中才有；sample_grid 为执行中逐样本累积的实时状态网格，result 生成后由 result.sample_grid 接管
  "result": { /* BenchmarkResult，见 §4.2；未完成时为 null */ }
}
```

### 4.2 BenchmarkResult

```jsonc
{
  "metrics": { "accuracy": 0.85 },          // 指标名 -> 值
  "total_samples": 20,
  "completed_samples": 20,
  "failed_samples": 0,
  "model_usage": { "input_tokens": 12000, "output_tokens": 3000, "total_tokens": 15000 },
  "samples_preview": [],                     // ⚠️ 恒为空（不再随结果存储）；按需走 §2.7 读 .eval log
  "sample_grid": [                           // 全部样本的状态网格（紧凑）
    { "id": 1, "status": "success" },        // status: success / error / none
    { "id": 2, "status": "error" }
  ],
  "artifact_paths": ["/data/.../xxx.eval"],
  "engine": "inspect_evals@0.14.3",
  "engine_metadata": {},
  "status": "success",                       // success / partial_success / failed
  "error": null
}
```

样本状态语义（`sample_grid[].status`，只看是否拿到结果，不看答对答错）：

| status  | 含义                       | 方块颜色 |
|---------|----------------------------|----------|
| success | 执行成功，拿到结果（有分/有输出） | 绿       |
| error   | 执行报错，未拿到结果         | 红       |
| none    | 未执行 / 无任何产出         | 黄       |

---

## 5. 前端轮询策略

- 页面挂载后 `setInterval(tick, 2000)`，卸载时清除。
- 每次 `tick` 并发执行：
  1. `loadStats()` — 拉 §2.3 全局指标，刷新「进行中 / 累计任务」。
  2. `pollActive()` — 对当前页 `pending`/`running` 任务逐个拉 §2.4 更新进度/状态；任一任务终结（success/failed/stopped）则重载当前页列表。
- 提交 / 重试 / 停止 / 删除后立即 `loadTasks()` + `loadStats()` 同步刷新，无需等下一轮轮询。

---

## 6. 变更记录

| 日期       | 变更                                                                 |
|------------|----------------------------------------------------------------------|
| 2026-07-15 | 执行中样本网格全量渲染：未执行样本默认黄色占位，完成后逐个更新为绿/红。移除 50 条预览上限：`samples_preview` 不再随结果存储，`GET /<id>/samples/<sample_id>` 改为按需读取 `.eval` log 解析对应样本（无条数上限）。 |
| 2026-07-15 | 执行中实时样本网格：`progress.sample_grid` 由 `on_sample_end` hook 逐样本累积（reporter 1s 节流），前端执行中回退渲染该网格，完成后切换到 `result.sample_grid`。 |
| 2026-07-15 | 新增 `GET /stats`（全局状态计数）；新增 `GET /<id>/samples/<sample_id>`（样本预览懒加载）；列表/详情默认剥离 `samples_preview`，改回传 `samples_preview_count`。 |

// 后端统一响应结构
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// ── 认证 / 用户 ──
export interface Tenant {
  id: number
  slug: string
  name: string
  is_active?: boolean
  is_system?: boolean
}

export interface User {
  id: number
  username: string
  email: string
  role?: string
  is_superuser?: boolean
  is_active?: boolean
  current_tenant?: Tenant
  memberships?: Array<{ id: number; tenant_name: string; role_name?: string }>
  created_at?: string
}

// ── 模型配置 ──
export interface ModelConfig {
  id: number
  display_name: string
  model_name: string
  api_base_url: string
  api_protocol: string
  description?: string
  extra_params?: Record<string, unknown>
  has_api_key?: boolean
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface ModelTestResult {
  ok: boolean
  latency_ms: number
  sample_output: string | null
  error: string | null
  provider: string
  model: string
}

// ── Benchmark ──
export interface SuiteConfigField {
  key: string
  type: string
  label?: string
  default?: unknown
  min?: number
  max?: number
  step?: number
  precision?: number
  options?: Array<string | { label: string; value: unknown }>
  help?: string
  placeholder?: string
}

export interface SuiteDescriptor {
  key: string
  engine: string
  display_name: string
  category: string
  description?: string
  needs_judge: boolean
  needs_sandbox: boolean
  default_config: Record<string, unknown>
  config_schema: { fields?: SuiteConfigField[] }
  disabled: boolean
  disabled_reason?: string | null
  notes?: string | null
}

export interface BenchmarkResult {
  metrics: Record<string, number | string>
  total_samples: number
  completed_samples: number
  failed_samples: number
  model_usage: { input_tokens?: number; output_tokens?: number; total_tokens?: number }
  samples_preview: Array<{
    id: string | number
    input: string
    target: string
    output: string
    score: string
    explanation?: string | null
    error?: string | null
  }>
  artifact_paths: string[]
  engine: string
  status: string
  error?: string | null
}

export type TaskStatus = 'pending' | 'running' | 'success' | 'failed'

export interface BenchmarkTask {
  id: number
  task_type: string
  status: TaskStatus
  error_message?: string | null
  task_name: string
  notes?: string | null
  engine: string
  benchmark_suite: string
  target_model_id: number
  judge_model_id?: number | null
  target_model?: ModelConfig | null
  judge_model?: ModelConfig | null
  benchmark_config?: { execution_config?: Record<string, unknown>; suite_config?: Record<string, unknown> }
  result?: BenchmarkResult | null
  progress?: { completed: number; total: number; current_metrics?: Record<string, unknown> } | null
  created_at?: string
  started_at?: string | null
  completed_at?: string | null
}

// ── 任务日志 ──
export interface TaskLogEntry {
  ts: string | null
  level: string
  step: string
  event: string
  msg: string
  elapsed_ms: number
  data?: Record<string, unknown>
}

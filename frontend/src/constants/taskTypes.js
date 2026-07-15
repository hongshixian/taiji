export const BENCHMARK_TASK_TYPE = 'benchmark'
export const RED_TEAM_TASK_TYPE = 'red_team'

export const TASK_TYPE_ROUTES = {
  [BENCHMARK_TASK_TYPE]: '/tasks/benchmark',
  [RED_TEAM_TASK_TYPE]: '/tasks/red-team',
}

export const TASK_TYPE_LABELS = {
  [BENCHMARK_TASK_TYPE]: 'Benchmark 测评',
  [RED_TEAM_TASK_TYPE]: '自动红队测评',
}

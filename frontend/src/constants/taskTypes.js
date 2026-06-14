export const WEBPAGE_ANALYSIS_TASK_TYPE = 'webpage_content_analysis'
export const CSV_QUALITY_TASK_TYPE = 'csv_quality_check'
export const BENCHMARK_TASK_TYPE = 'benchmark'

export const TASK_TYPE_ROUTES = {
  [WEBPAGE_ANALYSIS_TASK_TYPE]: '/tasks/webpage-analysis',
  [CSV_QUALITY_TASK_TYPE]: '/tasks/csv-quality',
  [BENCHMARK_TASK_TYPE]: '/tasks/benchmark',
}

export const TASK_TYPE_LABELS = {
  [WEBPAGE_ANALYSIS_TASK_TYPE]: '网页内容分析',
  [CSV_QUALITY_TASK_TYPE]: 'CSV 数据质量检查',
  [BENCHMARK_TASK_TYPE]: 'Benchmark 测评',
}

export default {
  // 页面头部
  pageEyebrow: '任务 · Benchmark 测评',
  pageTitle: 'Benchmark 测评',
  pageDesc: '选择被测模型与评测集，由 Worker 异步驱动 inspect_evals 引擎执行标准化 Benchmark 评测。',
  newTask: '新建测评',

  // 指标
  metricActive: '进行中',
  metricTotal: '累计任务',
  metricSuites: '可用评测集',

  // 新建对话框
  dialogTitle: '新建 Benchmark 测评',
  sectionBasic: '基本信息',
  taskName: '任务名称',
  taskNamePlaceholder: '留空则自动生成：模型-评测集-时间',
  notes: '备注',
  notesPlaceholder: '记录本次评测的目的（可选）',
  sectionSuite: '评测集',
  suitePlaceholder: '请选择评测集',
  sectionTarget: '被测模型',
  model: '模型',
  targetModelPlaceholder: '选择已配置的模型',
  targetModelHint: '生成参数（temperature / max_tokens 等）来自模型管理页面，本次评测使用其固定值。',
  sectionJudge: '评委模型',
  judgeModelPlaceholder: '选择评委模型',
  judgeModelHint: '该评测集需要一个模型作为评委来判断答案质量。',
  sectionExecution: '执行控制',
  sampleCount: '样本数量',
  customSampleCount: '自定义样本数',
  advanced: '高级 (并发 / 重复次数 / 超时)',
  maxConnections: '并发数',
  epochs: '重复次数',
  timeoutMinutes: '超时(分钟)',
  suiteParams: 'Suite 特有参数',
  submitTask: '提交任务',

  // 样本数量预设
  presetSmoke: '快速冒烟 (20)',
  presetStandard: '标准 (200)',
  presetFull: '完整',
  presetCustom: '自定义',

  // Suite 分组
  categoryCapability: '能力评测',
  categorySafety: '安全评测',
  categoryAlignment: '对齐/行为评测',

  // 进行中
  inProgress: '进行中',
  unnamed: '(未命名)',
  waitingWorker: '等待 Worker 拾取…',
  preparing: '准备中…',

  // 历史
  history: '历史记录',
  taskList: '任务列表',
  emptyTasks: '还没有创建任何评测任务',
  stop: '停止',
  stopSuccess: '任务已停止',
  stopFailed: '停止失败',
  emptyHistory: '还没有已完成的评测任务',

  // 表格列
  colTask: '任务',
  colSuite: '评测集',
  colTargetModel: '被测模型',
  colMetric: '主指标',
  colProgress: '进度',

  // 操作
  log: '日志',

  // 提示/toast
  loadTasksFailed: '加载任务失败',
  loadSuitesFailed: '加载评测集失败',
  selectSuiteWarn: '请选择评测集',
  selectTargetWarn: '请选择被测模型',
  needJudgeWarn: '该评测集需要评委模型',
  submitSuccess: '任务已提交',
  submitFailed: '提交失败',
  retrySuccess: '已重新提交',
  retryFailed: '重试失败',
  deleteConfirm: '确认删除这条评测任务？',
  deleteFailed: '删除失败',

  // 结果卡片 (BenchmarkResultCard)
  execFailed: '评测执行失败',
  noResultFailed: '任务失败，未产出结果',
  noResultYet: '任务尚未产出结果',
  mainMetrics: '主要指标',
  noMetrics: '暂无指标',
  sampleStats: '样本统计',
  sampleTotal: '总数',
  sampleCompleted: '已完成',
  sampleFailed: '失败',
  tokenUsage: 'Token 消耗',
  tokenInput: '输入',
  tokenOutput: '输出',
  tokenTotal: '合计',
  engine: '引擎',
  metaTarget: '被测',
  metaJudge: '评委',
  sampleDistribution: '样本状态（{n} 条）',
  sampleDistributionRunning: '样本状态 · 执行中 {done}/{total}',
  sampleSuccess: '执行成功',
  sampleError: '执行失败',
  sampleNone: '未执行',
  viewFullLog: '查看完整日志',
  sampleLimitHint: '提示：仅前 {n} 条样本可查看完整内容，其余方块仅展示执行状态。',
  sampleDialogTitle: '样本 #{id}',
  sampleNoDetailPrefix: '该样本超出预览范围，仅记录了执行状态。完整内容请',
  sampleNoDetailSuffix: '。',

  // 日志弹窗 (TaskLogDialog)
  logDialogTitle: '任务日志',
  logCount: '{n} 条',
  noLogs: '暂无执行日志',
  logInfo: '信息',
  logWarn: '警告',
  logError: '错误',
  loadLogsFailed: '加载任务日志失败',
}

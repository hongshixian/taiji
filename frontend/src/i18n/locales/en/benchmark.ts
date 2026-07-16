export default {
  // Page header
  pageEyebrow: 'Tasks · Benchmark Evaluation',
  pageTitle: 'Benchmark Evaluation',
  pageDesc: 'Pick a target model and evaluation suite; the Worker drives the inspect_evals engine asynchronously to run standardized benchmark evaluations.',
  newTask: 'New Evaluation',

  // Metrics
  metricActive: 'In Progress',
  metricTotal: 'Total Tasks',
  metricSuites: 'Available Suites',

  // Create dialog
  dialogTitle: 'New Benchmark Evaluation',
  sectionBasic: 'Basic Info',
  taskName: 'Task Name',
  taskNamePlaceholder: 'Leave blank to auto-generate: model-suite-time',
  notes: 'Notes',
  notesPlaceholder: 'Record the purpose of this evaluation (optional)',
  sectionSuite: 'Evaluation Suite',
  suitePlaceholder: 'Select an evaluation suite',
  sectionTarget: 'Target Model',
  model: 'Model',
  targetModelPlaceholder: 'Select a configured model',
  sectionJudge: 'Judge Model',
  judgeModelPlaceholder: 'Select a judge model',
  judgeModelHint: 'This suite needs a model to act as judge and assess answer quality.',
  sectionExecution: 'Execution Control',
  sampleCount: 'Sample Count',
  customSampleCount: 'Custom Sample Count',
  advanced: 'Advanced (Concurrency / Epochs / Timeout)',
  maxConnections: 'Concurrency',
  epochs: 'Epochs',
  timeoutMinutes: 'Timeout (min)',
  suiteParams: 'Suite-specific Parameters',
  submitTask: 'Submit Task',

  // Sample count presets
  presetFull: 'Full',
  presetPartial: 'Partial',

  // Suite groups
  categoryCapability: 'Capability',
  categorySafety: 'Safety',
  categoryAlignment: 'Alignment / Behavior',

  // In progress
  inProgress: 'In Progress',
  unnamed: '(unnamed)',
  waitingWorker: 'Waiting for a Worker to pick up…',
  preparing: 'Preparing…',

  // History
  history: 'History',
  taskList: 'Task List',
  emptyTasks: 'No evaluation tasks yet',
  stop: 'Stop',
  stopSuccess: 'Task stopped',
  stopFailed: 'Failed to stop',
  emptyHistory: 'No completed evaluation tasks yet',

  // Table columns
  colTask: 'Task',
  colSuite: 'Suite',
  colTargetModel: 'Target Model',
  colMetric: 'Primary Metric',
  colProgress: 'Progress',

  // Actions
  log: 'Logs',

  // Hints / toasts
  loadTasksFailed: 'Failed to load tasks',
  loadSuitesFailed: 'Failed to load evaluation suites',
  selectSuiteWarn: 'Please select an evaluation suite',
  selectTargetWarn: 'Please select a target model',
  needJudgeWarn: 'This suite requires a judge model',
  submitSuccess: 'Task submitted',
  submitFailed: 'Submit failed',
  retrySuccess: 'Resubmitted',
  retryFailed: 'Retry failed',
  deleteConfirm: 'Delete this evaluation task?',
  deleteFailed: 'Delete failed',

  // Result card (BenchmarkResultCard)
  execFailed: 'Evaluation failed',
  noResultFailed: 'Task failed, no results produced',
  noResultYet: 'Task has not produced results yet',
  mainMetrics: 'Key Metrics',
  noMetrics: 'No metrics',
  sampleStats: 'Sample Stats',
  sampleTotal: 'Total',
  sampleCompleted: 'Completed',
  sampleFailed: 'Failed',
  tokenUsage: 'Token Usage',
  tokenInput: 'Input',
  tokenOutput: 'Output',
  tokenTotal: 'Total',
  engine: 'Engine',
  metaTarget: 'Target',
  metaJudge: 'Judge',
  sampleDistribution: 'Sample Status ({n})',
  sampleDistributionRunning: 'Sample Status · Running {done}/{total}',
  sampleSuccess: 'Succeeded',
  sampleError: 'Failed',
  sampleNone: 'Not run',
  viewFullLog: 'View full logs',
  sampleDialogTitle: 'Sample #{id}',
  sampleNoDetailPrefix: 'Failed to load this sample. For full content, ',
  sampleNoDetailSuffix: '.',

  // Log dialog (TaskLogDialog)
  logDialogTitle: 'Task Logs',
  logCount: '{n} entries',
  noLogs: 'No execution logs',
  logInfo: 'Info',
  logWarn: 'Warning',
  logError: 'Error',
  loadLogsFailed: 'Failed to load task logs',
}

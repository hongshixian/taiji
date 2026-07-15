export default {
  // Page header
  pageEyebrow: 'Tasks · Automated Red Teaming',
  pageTitle: 'Automated Red Teaming',
  pageDesc: 'Choose a red-team attack method to launch automated adversarial tests against the target model and assess its safety boundaries.',
  newTask: 'New Evaluation',

  // Metrics
  inProgress: 'In Progress',
  history: 'History',
  pollInterval: 'Poll Interval',
  pollIntervalValue: '2s',

  // Create dialog
  dialogTitle: 'New Automated Red Team Evaluation',
  taskName: 'Task Name',
  taskNamePlaceholder: 'e.g. GPT-4o safety boundary test',
  targetModel: 'Target Model',
  targetModelPlaceholder: 'Select a configured model',
  attackMethod: 'Red Team Method',
  attackMethodPlaceholder: 'Select a red-team attack method',
  submitTask: 'Submit Evaluation',

  // In progress
  submittingPlaceholder: 'Submitting…',
  log: 'Logs',
  waited: 'Waited',
  runningHint: 'Running in the background; will refresh automatically when done',

  // Table columns
  colTaskName: 'Task Name',
  colTargetModel: 'Target Model',
  colAttackMethod: 'Red Team Method',

  // Expanded detail
  infoTitle: 'Task Info',
  infoCreated: 'Created',
  infoCompleted: 'Completed',
  infoError: 'Error',
  attackConfigTitle: 'Attack Config',
  method: 'Method',
  defaultConfig: 'Using default config',
  resultTitle: 'Evaluation Result',
  noResult: 'No result yet',

  // Empty state
  emptyDesc: 'No red-team evaluations submitted yet',
  submitFirst: 'Submit your first evaluation',

  // Red team methods (keep codes, translate descriptions)
  methodGcg: 'GCG (Greedy Coordinate Gradient attack)',
  methodGcgEnsemble: 'GCG Ensemble (ensemble gradient attack)',
  methodGptfuzz: 'GPTFuzz (fuzzing attack)',
  methodPair: 'PAIR (Prompt Automatic Iterative Refinement)',
  methodTap: 'TAP (Tree of Attacks with Pruning)',
  methodAutodan: 'AutoDAN (automated DAN attack)',
  methodAutoprompt: 'AutoPrompt (automated prompt search)',

  // Form validation
  taskNameRequired: 'Please enter a task name',
  targetModelRequired: 'Please select a target model from the model library',
  attackMethodRequired: 'Please select a red-team method',

  // toast / confirm
  retrySuccess: 'Resubmitted',
  retryFailed: 'Retry failed: ',
  deleteConfirmMsg: 'Delete this evaluation task? This cannot be undone.',
  deleteConfirmTitle: 'Confirm Deletion',
  deleteConfirmBtn: 'Delete',
  deleteSuccess: 'Task deleted',
  deleteFailed: 'Delete failed: ',
  submitSuccess: 'Red-team evaluation task submitted',
  submitFailed: 'Submit failed',
  evalComplete: 'Red-team evaluation completed',
}

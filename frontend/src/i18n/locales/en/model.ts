export default {
  eyebrow: 'Resources · Model Library',
  title: 'Model Management',
  add: 'Add Model',
  lede: 'Configure the API details of the models under test so evaluation tasks can call them directly. Data belongs to the current tenant and is not visible to others.',
  showInactive: 'Show disabled',

  testBtn: 'Check',

  col: {
    displayName: 'Display Name',
    modelName: 'Model ID',
    protocol: 'Protocol',
    apiUrl: 'API URL',
  },

  empty: {
    eyebrow: 'No models',
    title: 'No models configured yet',
    desc: 'Maintain the API URL, key and other details of the models under test here. When creating an evaluation task you can pick directly from the library without re-entering them.',
    addFirst: 'Add your first model',
  },

  dialog: {
    editTitle: 'Edit Model',
    createTitle: 'Add Model',
  },

  field: {
    displayName: 'Display Name',
    displayNameHint: 'The name shown on leaderboards and task lists',
    displayNamePlaceholder: 'e.g. GPT-4o (OpenAI official)',
    modelName: 'Model ID',
    modelNameHint: 'Value of the "model" field in the API request body',
    modelNamePlaceholder: 'e.g. gpt-4o',
    protocol: 'API Protocol',
    apiUrl: 'API URL',
    apiKey: 'API Key',
    apiKeyPlaceholderEdit: 'Leave blank to keep the existing key',
    apiKeyPlaceholderCreate: 'sk-... (optional, stored encrypted)',
    descPlaceholder: 'Optional notes',
    genParams: 'Generation Parameters',
    genParamsHint: 'Evaluations use the sampling parameters configured here so results for the same model stay comparable. Leave blank to use the engine defaults.',
    stopSeq: 'Stop Sequences',
    stopPlaceholder: 'Comma-separated, optional',
    optionalPlaceholder: 'Optional',
  },

  proto: {
    openai: 'OpenAI-compatible',
    custom: 'Custom',
  },

  test: {
    title: 'Model Connectivity Test',
    sending: 'Sending a test request to the model…',
    modelLabel: 'Model: {name}',
    pass: 'Passed',
    fail: 'Failed',
    latency: 'Latency',
    sampleOutput: 'Sample Output',
    emptyOutput: '(empty)',
    errorInfo: 'Error',
    retest: 'Test again',
  },

  toast: {
    loadFailed: 'Failed to load the model list',
    fillDisplayName: 'Please enter a display name',
    fillModelName: 'Please enter a model ID',
    fillApiUrl: 'Please enter an API URL',
    added: 'Model added',
    testPass: 'Test passed ({ms}ms)',
    testFail: 'Test failed, check the error details',
    reqFailed: 'Request failed',
    testReqFailed: 'Test request failed',
  },

  remove: {
    message: 'Delete model "{name}"? This cannot be undone. Historical tasks linked to it are not affected.',
    title: 'Confirm Deletion',
    confirmText: 'Delete',
  },
}

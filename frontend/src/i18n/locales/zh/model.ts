export default {
  eyebrow: '资源 · 模型库',
  title: '模型管理',
  add: '添加模型',
  lede: '配置被测模型的 API 信息，供测评任务直接调用。数据归属当前租户，其他租户不可见。',

  testBtn: '检测',

  col: {
    displayName: '显示名称',
    modelName: '模型标识',
    protocol: '协议',
    apiUrl: 'API 地址',
  },

  empty: {
    eyebrow: '暂无模型',
    title: '还没有配置任何模型',
    desc: '在这里维护被测模型的 API 地址、密钥等信息，创建测评任务时可直接从模型库选择，无需重复填写。',
    addFirst: '添加第一个模型',
  },

  dialog: {
    editTitle: '编辑模型配置',
    createTitle: '添加模型',
  },

  field: {
    displayName: '显示名称',
    displayNameHint: '显示在测评榜单和任务列表中的名称',
    displayNamePlaceholder: '例：GPT-4o（OpenAI 官方）',
    modelName: '模型标识',
    modelNameHint: 'API 请求 body 中的 model 字段值',
    modelNamePlaceholder: '例：gpt-4o',
    protocol: 'API 协议',
    apiUrl: 'API 地址',
    apiKey: 'API Key',
    apiKeyPlaceholderEdit: '留空则不修改原有密钥',
    apiKeyPlaceholderCreate: 'sk-...（可选，加密存储）',
    descPlaceholder: '可选的备注说明',
    genParams: '生成参数',
    genParamsHint: '评测时将统一使用这里配置的采样参数，保证同一模型的结果可比。留空则由引擎使用默认值。',
    stopSeq: 'Stop 序列',
    stopPlaceholder: '逗号分隔，可选',
    optionalPlaceholder: '可选',
  },

  proto: {
    openai: 'OpenAI 兼容',
    custom: '自定义',
  },

  test: {
    title: '模型连通性检测',
    sending: '正在向模型发送测试请求…',
    modelLabel: '模型：{name}',
    pass: '通过',
    fail: '失败',
    latency: '耗时',
    sampleOutput: '样例输出',
    emptyOutput: '(空)',
    errorInfo: '错误信息',
    retest: '重新测试',
  },

  toast: {
    loadFailed: '加载模型列表失败',
    fillDisplayName: '请填写显示名称',
    fillModelName: '请填写模型标识',
    fillApiUrl: '请填写 API 地址',
    added: '模型已添加',
    testPass: '测试通过（{ms}ms）',
    testFail: '测试失败，请查看错误详情',
    reqFailed: '请求失败',
    testReqFailed: '测试请求失败',
  },

  remove: {
    message: '确定删除模型「{name}」？删除后不可恢复，已关联该模型的历史任务不受影响。',
    title: '删除确认',
    confirmText: '确认删除',
  },
}

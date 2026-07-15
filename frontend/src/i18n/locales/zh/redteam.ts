export default {
  // 页面头部
  pageEyebrow: '任务 · 自动红队测评',
  pageTitle: '自动红队测评',
  pageDesc: '选择红队攻击方法对目标模型发起自动化对抗测试，评估模型安全边界。',
  newTask: '新建测评',

  // 指标
  inProgress: '进行中',
  history: '历史记录',
  pollInterval: '轮询间隔',
  pollIntervalValue: '2 秒',

  // 新建对话框
  dialogTitle: '新建自动红队测评',
  taskName: '任务名称',
  taskNamePlaceholder: '例：GPT-4o 安全边界测试',
  targetModel: '被测模型',
  targetModelPlaceholder: '选择已配置的模型',
  attackMethod: '红队方法',
  attackMethodPlaceholder: '选择红队攻击方法',
  submitTask: '提交测评',

  // 进行中
  submittingPlaceholder: '提交中…',
  log: '日志',
  waited: '已等待',
  runningHint: '后台执行中，完成后自动刷新',

  // 表格列
  colTaskName: '任务名称',
  colTargetModel: '目标模型',
  colAttackMethod: '红队方法',

  // 展开详情
  infoTitle: '任务信息',
  infoCreated: '创建',
  infoCompleted: '完成',
  infoError: '错误',
  attackConfigTitle: '攻击配置',
  method: '方法',
  defaultConfig: '使用默认配置',
  resultTitle: '测评结果',
  noResult: '暂无结果',

  // 空状态
  emptyDesc: '还没有提交过红队测评',
  submitFirst: '提交第一个测评',

  // 红队方法（代号保留，说明翻译）
  methodGcg: 'GCG（贪婪坐标梯度攻击）',
  methodGcgEnsemble: 'GCG Ensemble（集成梯度攻击）',
  methodGptfuzz: 'GPTFuzz（模糊测试攻击）',
  methodPair: 'PAIR（提示自动迭代精炼）',
  methodTap: 'TAP（树状攻击与剪枝）',
  methodAutodan: 'AutoDAN（自动化 DAN 攻击）',
  methodAutoprompt: 'AutoPrompt（自动提示搜索）',

  // 表单校验
  taskNameRequired: '请填写任务名称',
  targetModelRequired: '请从模型库选择被测模型',
  attackMethodRequired: '请选择红队方法',

  // toast / confirm
  retrySuccess: '已重新提交',
  retryFailed: '重试失败：',
  deleteConfirmMsg: '确定删除该测评任务？删除后不可恢复。',
  deleteConfirmTitle: '删除确认',
  deleteConfirmBtn: '确认删除',
  deleteSuccess: '任务已删除',
  deleteFailed: '删除失败：',
  submitSuccess: '红队测评任务已提交',
  submitFailed: '提交失败',
  evalComplete: '红队测评完成',
}

export default {
  eyebrow: '超级管理员 · 平台配置',
  title: '系统设置',
  lede: '平台级集成配置和 IAM 平台管理员名册。修改这里的设置会影响整个平台。',

  benchmark: {
    eyebrow: '评测集成',
    title: 'Benchmark 集成设置',
    desc: 'HuggingFace 访问令牌用于加载 gated 数据集。',
    hfToken: 'HuggingFace Token',
    hfTokenHint: '留空则不修改；保存后不会再回显。',
    hfTokenPlaceholderSet: '已保存（不回显；留空保持不变）',
    hfTokenPlaceholderUnset: '例：hf_xxxxxxxx（可选）',
    hfTokenEmptyWarn: '请输入 HuggingFace Token 后再保存。',
  },

  superuser: {
    eyebrow: '权限',
    title: '平台管理员',
    desc: '由 IAM 统一管理的平台运营账号。无法移除自己的平台管理员身份。',
    identifierPlaceholder: '用户名或邮箱',
    colUsername: '用户名',
    colEmail: '邮箱',
    colMemberships: '加入租户',
    remove: '移除',
  },

  toast: {
    saveFailed: '保存失败',
    loadSuperusersFailed: '加载平台管理员失败',
    enterIdentifier: '请输入用户名或邮箱',
    added: '已添加',
    addFailed: '添加失败',
    removed: '已移除',
    removeFailed: '移除失败',
  },

  removeConfirm: {
    message: '确定移除「{name}」的平台管理员权限吗？',
    title: '移除平台管理员',
    confirmText: '移除',
  },
}

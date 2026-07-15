export default {
  eyebrow: 'Superadmin · Platform Config',
  title: 'System Settings',
  lede: 'Platform-level key/value configuration and the superadmin roster. Changes here affect the whole platform.',

  registration: {
    eyebrow: 'Registration Policy',
    title: 'Default Registration Tenant',
    desc: 'Newly self-registered users are automatically added to the tenant selected here.',
    defaultTenant: 'Default Tenant',
  },

  benchmark: {
    eyebrow: 'Evaluation Integration',
    title: 'Benchmark Integration',
    desc: 'The HuggingFace access token is used to load gated datasets; the default judge model is pre-filled for benchmarks that require a judge.',
    hfToken: 'HuggingFace Token',
    hfTokenHint: 'Leave blank to keep unchanged; it will not be shown again after saving.',
    hfTokenPlaceholderSet: 'Saved (hidden; leave blank to keep unchanged)',
    hfTokenPlaceholderUnset: 'e.g. hf_xxxxxxxx (optional)',
    judgeModel: 'Default Judge Model',
    judgeModelPlaceholder: 'Pick a model as the default judge',
  },

  superuser: {
    eyebrow: 'Permissions',
    title: 'Superadmins',
    desc: 'Platform operation accounts that bypass permission checks. You cannot remove your own superadmin status.',
    identifierPlaceholder: 'Username or email',
    colUsername: 'Username',
    colEmail: 'Email',
    colMemberships: 'Tenants',
    remove: 'Remove',
  },

  toast: {
    selectTenant: 'Please select a default registration tenant',
    saveFailed: 'Failed to save',
    loadSuperusersFailed: 'Failed to load superadmins',
    enterIdentifier: 'Please enter a username or email',
    added: 'Added',
    addFailed: 'Failed to add',
    removed: 'Removed',
    removeFailed: 'Failed to remove',
  },

  removeConfirm: {
    message: 'Remove superadmin privileges from "{name}"?',
    title: 'Remove Superadmin',
    confirmText: 'Remove',
  },
}

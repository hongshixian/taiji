export default {
  eyebrow: 'Superadmin · Platform Config',
  title: 'System Settings',
  lede: 'Platform integration configuration and the IAM platform administrator roster. Changes here affect the whole platform.',

  benchmark: {
    eyebrow: 'Evaluation Integration',
    title: 'Benchmark Integration',
    desc: 'The HuggingFace access token is used to load gated datasets.',
    hfToken: 'HuggingFace Token',
    hfTokenHint: 'Leave blank to keep unchanged; it will not be shown again after saving.',
    hfTokenPlaceholderSet: 'Saved (hidden; leave blank to keep unchanged)',
    hfTokenPlaceholderUnset: 'e.g. hf_xxxxxxxx (optional)',
    hfTokenEmptyWarn: 'Enter a HuggingFace token before saving.',
  },

  superuser: {
    eyebrow: 'Permissions',
    title: 'Platform Administrators',
    desc: 'Platform operation accounts managed by IAM. You cannot remove your own platform administrator status.',
    identifierPlaceholder: 'Username or email',
    colUsername: 'Username',
    colEmail: 'Email',
    colMemberships: 'Tenants',
    remove: 'Remove',
  },

  toast: {
    saveFailed: 'Failed to save',
    loadSuperusersFailed: 'Failed to load platform administrators',
    enterIdentifier: 'Please enter a username or email',
    added: 'Added',
    addFailed: 'Failed to add',
    removed: 'Removed',
    removeFailed: 'Failed to remove',
  },

  removeConfirm: {
    message: 'Remove platform administrator privileges from "{name}"?',
    title: 'Remove Platform Administrator',
    confirmText: 'Remove',
  },
}

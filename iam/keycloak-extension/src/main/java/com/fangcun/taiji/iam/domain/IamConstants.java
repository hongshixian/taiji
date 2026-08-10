package com.fangcun.taiji.iam.domain;

public final class IamConstants {
    public static final String USER_GLOBAL_ID = "fc_global_user_id";
    public static final String TENANT_GLOBAL_ID = "fc_global_tenant_id";
    public static final String TENANT_TYPE = "fc_tenant_type";
    public static final String TENANT_STATUS = "fc_lifecycle_status";
    public static final String TENANT_OWNER_ID = "fc_owner_user_id";
    public static final String TENANT_PROTECTED = "fc_protected";
    public static final String INITIAL_ADMIN_INVITATION_ID = "fc_initial_admin_invitation_id";
    public static final String INVITATION_ROLE_PREFIX = "fc_invitation_role_";
    public static final String IDEMPOTENCY_FINGERPRINT = "fc_idempotency_fingerprint";

    public static final String TYPE_PERSONAL = "personal";
    public static final String TYPE_ENTERPRISE = "enterprise";
    public static final String STATUS_PENDING = "pending";
    public static final String STATUS_ACTIVE = "active";
    public static final String STATUS_DISABLED = "disabled";

    public static final String GROUP_TENANT_ADMIN = "fc-role-tenant-admin";
    public static final String GROUP_MEMBER = "fc-role-member";
    public static final String GROUP_DISABLED = "fc-membership-disabled";

    public static final int DEFAULT_INVITATION_TTL_SECONDS = 7 * 24 * 60 * 60;

    private IamConstants() {
    }
}

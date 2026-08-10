package com.fangcun.taiji.iam.domain;

import java.util.Locale;

public enum TenantRole {
    TENANT_ADMIN("tenant_admin", IamConstants.GROUP_TENANT_ADMIN),
    MEMBER("member", IamConstants.GROUP_MEMBER);

    private final String apiValue;
    private final String groupName;

    TenantRole(String apiValue, String groupName) {
        this.apiValue = apiValue;
        this.groupName = groupName;
    }

    public String apiValue() {
        return apiValue;
    }

    public String groupName() {
        return groupName;
    }

    public static TenantRole fromApiValue(String value) {
        if (value == null || value.isBlank()) {
            return MEMBER;
        }
        String normalized = value.trim().toLowerCase(Locale.ROOT);
        for (TenantRole role : values()) {
            if (role.apiValue.equals(normalized)) {
                return role;
            }
        }
        throw new IamApiException(400, "invalid_role", "role 必须是 tenant_admin 或 member");
    }
}

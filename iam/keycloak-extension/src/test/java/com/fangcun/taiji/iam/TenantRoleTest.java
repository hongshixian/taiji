package com.fangcun.taiji.iam;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.fangcun.taiji.iam.domain.IamApiException;
import com.fangcun.taiji.iam.domain.TenantRole;
import org.junit.jupiter.api.Test;

class TenantRoleTest {
    @Test
    void defaultsToMember() {
        assertEquals(TenantRole.MEMBER, TenantRole.fromApiValue(null));
        assertEquals(TenantRole.MEMBER, TenantRole.fromApiValue(" "));
    }

    @Test
    void acceptsOnlyFixedRoles() {
        assertEquals(TenantRole.TENANT_ADMIN, TenantRole.fromApiValue("TENANT_ADMIN"));
        assertEquals(TenantRole.MEMBER, TenantRole.fromApiValue("member"));
        assertThrows(IamApiException.class, () -> TenantRole.fromApiValue("custom"));
    }
}

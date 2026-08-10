package com.fangcun.taiji.iam.domain;

import static com.fangcun.taiji.iam.domain.IamConstants.DEFAULT_INVITATION_TTL_SECONDS;
import static com.fangcun.taiji.iam.domain.IamConstants.GROUP_DISABLED;
import static com.fangcun.taiji.iam.domain.IamConstants.INITIAL_ADMIN_INVITATION_ID;
import static com.fangcun.taiji.iam.domain.IamConstants.INVITATION_ROLE_PREFIX;
import static com.fangcun.taiji.iam.domain.IamConstants.IDEMPOTENCY_FINGERPRINT;
import static com.fangcun.taiji.iam.domain.IamConstants.STATUS_ACTIVE;
import static com.fangcun.taiji.iam.domain.IamConstants.STATUS_DISABLED;
import static com.fangcun.taiji.iam.domain.IamConstants.STATUS_PENDING;
import static com.fangcun.taiji.iam.domain.IamConstants.TENANT_GLOBAL_ID;
import static com.fangcun.taiji.iam.domain.IamConstants.TENANT_OWNER_ID;
import static com.fangcun.taiji.iam.domain.IamConstants.TENANT_PROTECTED;
import static com.fangcun.taiji.iam.domain.IamConstants.TENANT_STATUS;
import static com.fangcun.taiji.iam.domain.IamConstants.TENANT_TYPE;
import static com.fangcun.taiji.iam.domain.IamConstants.TYPE_ENTERPRISE;
import static com.fangcun.taiji.iam.domain.IamConstants.TYPE_PERSONAL;
import static com.fangcun.taiji.iam.domain.IamConstants.USER_GLOBAL_ID;

import java.time.Instant;
import java.util.AbstractMap;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;

import org.keycloak.models.GroupModel;
import org.keycloak.models.OrganizationInvitationModel;
import org.keycloak.models.OrganizationModel;
import org.keycloak.models.RealmModel;
import org.keycloak.models.RoleModel;
import org.keycloak.models.UserModel;
import org.keycloak.models.KeycloakSession;
import org.keycloak.organization.InvitationManager;
import org.keycloak.organization.OrganizationProvider;

import com.fangcun.taiji.iam.events.IamEventPublisher;

public final class IdentityProvisioningService {
    private static final Pattern EMAIL_PATTERN = Pattern.compile("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$");

    private final KeycloakSession session;
    private final RealmModel realm;
    private final OrganizationProvider organizations;
    private final IamEventPublisher publisher;

    public IdentityProvisioningService(KeycloakSession session) {
        this(session, null);
    }

    public IdentityProvisioningService(KeycloakSession session, IamEventPublisher publisher) {
        this.session = session;
        this.realm = session.getContext().getRealm();
        this.organizations = session.getProvider(OrganizationProvider.class);
        this.publisher = publisher;
        if (organizations == null || !organizations.isEnabled()) {
            throw new IamApiException(503, "organizations_disabled", "Realm Organizations 尚未启用");
        }
    }

    public String ensureStableUserId(UserModel user) {
        String globalId = user.getFirstAttribute(USER_GLOBAL_ID);
        if (globalId == null || globalId.isBlank()) {
            globalId = UUID.randomUUID().toString();
            user.setSingleAttribute(USER_GLOBAL_ID, globalId);
        }
        return globalId;
    }

    public OrganizationModel ensurePersonalTenant(UserModel user) {
        String userGlobalId = ensureStableUserId(user);
        String alias = "personal-" + userGlobalId;
        OrganizationModel organization = organizations.getByAlias(alias);

        boolean created = organization == null;
        if (created) {
            organization = organizations.create(user.getUsername() + " 的个人空间", alias);
        }

        organization.setName(user.getUsername() + " 的个人空间");
        setAttribute(organization, TENANT_GLOBAL_ID,
                attribute(organization, TENANT_GLOBAL_ID, UUID.randomUUID().toString()));
        setAttribute(organization, TENANT_TYPE, TYPE_PERSONAL);
        setAttribute(organization, TENANT_STATUS, STATUS_ACTIVE);
        setAttribute(organization, TENANT_OWNER_ID, userGlobalId);
        setAttribute(organization, TENANT_PROTECTED, "true");
        organization.setEnabled(true);
        boolean membershipChanged = assignRole(organization, user, TenantRole.TENANT_ADMIN);
        if (created) {
            emit("iam.tenant.created.v1", stableTenantId(organization), Map.of("tenant_type", TYPE_PERSONAL));
        }
        if (membershipChanged) {
            emitMembership("iam.membership.created.v1", organization, user, TenantRole.TENANT_ADMIN);
        }
        return organization;
    }

    public void provisionRegisteredUser(UserModel user) {
        ensurePersonalTenant(user);
        acceptPendingInvitations(user);
    }

    public List<Map<String, Object>> listUserTenants(UserModel user) {
        ensurePersonalTenant(user);
        return organizations.getByMember(user)
                .map(organization -> new AbstractMap.SimpleImmutableEntry<>(
                        organization, roleOf(organization, user)))
                .filter(entry -> entry.getValue() != null)
                .filter(entry -> entry.getKey().isEnabled())
                .filter(entry -> STATUS_ACTIVE.equals(attribute(entry.getKey(), TENANT_STATUS, STATUS_ACTIVE)))
                .sorted(Comparator.comparing(entry -> !TYPE_PERSONAL.equals(
                        attribute(entry.getKey(), TENANT_TYPE, TYPE_ENTERPRISE))))
                .map(entry -> tenantToMap(entry.getKey(), entry.getValue()))
                .toList();
    }

    public OrganizationModel createEnterpriseTenant(
            String name,
            String initialAdminIdentifier,
            String idempotencyKey,
            String actorGlobalId) {
        String normalizedName = requireText(name, "name", 100);
        String identifier = requireText(initialAdminIdentifier, "initial_admin", 254);
        String globalId = IdempotencyKey.deterministicUuid(
                realm.getName() + ":" + actorGlobalId + ":create-enterprise", idempotencyKey);
        String fingerprint = IdempotencyKey.fingerprint(normalizedName, identifier);
        OrganizationModel organization = organizations.getByAlias("enterprise-" + globalId);
        if (organization != null) {
            if (!fingerprint.equals(attribute(organization, IDEMPOTENCY_FINGERPRINT, null))) {
                throw new IamApiException(
                        409, "idempotency_conflict", "该 Idempotency-Key 已用于不同的请求参数");
            }
            return organization;
        }
        organization = organizations.create(normalizedName, "enterprise-" + globalId);

        setAttribute(organization, TENANT_GLOBAL_ID, globalId);
        setAttribute(organization, IDEMPOTENCY_FINGERPRINT, fingerprint);
        setAttribute(organization, TENANT_TYPE, TYPE_ENTERPRISE);
        setAttribute(organization, TENANT_STATUS, STATUS_PENDING);
        setAttribute(organization, TENANT_PROTECTED, "false");

        UserModel initialAdmin = findUser(identifier);
        if (initialAdmin != null) {
            requireHumanUser(initialAdmin);
            if (!initialAdmin.isEnabled()) {
                throw new IamApiException(409, "initial_admin_disabled", "初始管理员账号已停用");
            }
            ensureStableUserId(initialAdmin);
            assignRole(organization, initialAdmin, TenantRole.TENANT_ADMIN);
            setAttribute(organization, TENANT_STATUS, STATUS_ACTIVE);
        } else {
            if (!EMAIL_PATTERN.matcher(identifier).matches()) {
                throw new IamApiException(404, "user_not_found", "初始管理员不存在；未注册用户必须使用完整邮箱");
            }
            OrganizationInvitationModel invitation = createInvitation(
                    organization, identifier, TenantRole.TENANT_ADMIN);
            setAttribute(organization, INITIAL_ADMIN_INVITATION_ID, invitation.getId());
        }
        emit("iam.tenant.created.v1", globalId, Map.of(
                "tenant_type", TYPE_ENTERPRISE,
                "lifecycle_status", attribute(organization, TENANT_STATUS, STATUS_PENDING)));
        if (initialAdmin != null) {
            emitMembership("iam.membership.created.v1", organization, initialAdmin, TenantRole.TENANT_ADMIN);
        }
        return organization;
    }

    public OrganizationModel updateEnterpriseTenant(String tenantId, String name, Boolean enabled) {
        OrganizationModel organization = requireTenant(tenantId);
        requireEnterprise(organization);

        if (name != null) {
            organization.setName(requireText(name, "name", 100));
        }
        if (enabled != null) {
            if (enabled && activeAdminCount(organization) == 0) {
                throw new IamApiException(409, "tenant_has_no_admin", "没有有效租户管理员，不能启用租户");
            }
            organization.setEnabled(enabled);
            setAttribute(organization, TENANT_STATUS, enabled ? STATUS_ACTIVE : STATUS_DISABLED);
        }
        emit(enabled != null && !enabled ? "iam.tenant.disabled.v1" : "iam.tenant.updated.v1",
                stableTenantId(organization),
                Map.of("lifecycle_status", attribute(organization, TENANT_STATUS, STATUS_ACTIVE)));
        return organization;
    }

    public List<Map<String, Object>> listMembers(String tenantId) {
        OrganizationModel organization = requireTenant(tenantId);
        return organizations.getMembersStream(organization, Map.of(), null, null, null)
                .map(user -> memberToMap(organization, user))
                .sorted(Comparator.comparing(entry -> (String) entry.get("username")))
                .toList();
    }

    public Map<String, Object> addMember(String tenantId, String identifier, TenantRole role) {
        OrganizationModel organization = requireTenant(tenantId);
        requireEnterprise(organization);
        requireActiveTenant(organization);
        String exactIdentifier = requireText(identifier, "identifier", 254);
        UserModel user = findUser(exactIdentifier);

        if (user == null) {
            if (!EMAIL_PATTERN.matcher(exactIdentifier).matches()) {
                throw new IamApiException(404, "user_not_found", "用户不存在；邀请未注册用户必须使用完整邮箱");
            }
            return invitationToMap(createInvitation(organization, exactIdentifier, role));
        }

        requireHumanUser(user);
        if (!user.isEnabled()) {
            throw new IamApiException(409, "user_disabled", "用户账号已停用");
        }
        ensureStableUserId(user);
        boolean existingMember = organizations.isMember(organization, user);
        boolean changed = assignRole(organization, user, role);
        if (changed) {
            emitMembership(existingMember ? "iam.membership.updated.v1" : "iam.membership.created.v1",
                    organization, user, role);
        }
        return memberToMap(organization, user);
    }

    public Map<String, Object> updateMember(
            String tenantId, String userId, TenantRole role, Boolean active) {
        OrganizationModel organization = requireTenant(tenantId);
        requireEnterprise(organization);
        UserModel user = requireMemberUser(organization, userId);
        TenantRole currentRole = roleOf(organization, user);

        if (Boolean.FALSE.equals(active)) {
            deactivateMember(organization, user, currentRole);
        } else if (role != null) {
            if (currentRole == TenantRole.TENANT_ADMIN
                    && role != TenantRole.TENANT_ADMIN
                    && activeAdminCount(organization) <= 1) {
                throw new IamApiException(409, "last_tenant_admin", "不能降级最后一名租户管理员");
            }
            if (assignRole(organization, user, role)) {
                emitMembership("iam.membership.updated.v1", organization, user, role);
            }
        } else if (Boolean.TRUE.equals(active) && currentRole == null) {
            assignRole(organization, user, TenantRole.MEMBER);
            emitMembership("iam.membership.updated.v1", organization, user, TenantRole.MEMBER);
        }
        return memberToMap(organization, user);
    }

    public Map<String, Object> deactivateMember(String tenantId, String userId) {
        OrganizationModel organization = requireTenant(tenantId);
        requireEnterprise(organization);
        UserModel user = requireMemberUser(organization, userId);
        deactivateMember(organization, user, roleOf(organization, user));
        return memberToMap(organization, user);
    }

    public Map<String, Object> resendInvitation(String invitationId) {
        OrganizationInvitationModel invitation = requireInvitation(invitationId);
        OrganizationModel organization = organizations.getById(invitation.getOrganizationId());
        invitation.setExpiresAt((int) Instant.now().getEpochSecond() + DEFAULT_INVITATION_TTL_SECONDS);
        emit("iam.invitation.updated.v1", invitation.getId(), Map.of(
                "tenant_id", stableTenantId(organization),
                "action", "resent"));
        return invitationToMap(invitation);
    }

    public void revokeInvitation(String invitationId) {
        OrganizationInvitationModel invitation = requireInvitation(invitationId);
        OrganizationModel organization = organizations.getById(invitation.getOrganizationId());
        if (invitation.getId().equals(attribute(organization, INITIAL_ADMIN_INVITATION_ID, null))) {
            throw new IamApiException(
                    409, "initial_admin_invitation_required", "初始管理员邀请不能撤销，只能重发");
        }
        organizations.getInvitationManager().remove(invitation.getId());
        removeAttribute(organization, INVITATION_ROLE_PREFIX + invitation.getId());
        emit("iam.invitation.updated.v1", invitation.getId(), Map.of(
                "tenant_id", stableTenantId(organization),
                "action", "revoked"));
    }

    public OrganizationModel tenantForInvitation(String invitationId) {
        OrganizationInvitationModel invitation = requireInvitation(invitationId);
        OrganizationModel organization = organizations.getById(invitation.getOrganizationId());
        if (organization == null) {
            throw new IamApiException(404, "tenant_not_found", "邀请所属租户不存在");
        }
        return organization;
    }

    public OrganizationModel requireTenant(String globalTenantId) {
        String expected = requireText(globalTenantId, "tenant_id", 64);
        return organizations.getAllStream()
                .filter(org -> expected.equals(attribute(org, TENANT_GLOBAL_ID, null)))
                .findFirst()
                .orElseThrow(() -> new IamApiException(404, "tenant_not_found", "租户不存在"));
    }

    public TenantRole roleOf(OrganizationModel organization, UserModel user) {
        List<GroupModel> groups = organizations.getOrganizationGroupsByMember(organization, user).toList();
        if (groups.stream().anyMatch(group -> GROUP_DISABLED.equals(group.getName()))) {
            return null;
        }
        if (groups.stream().anyMatch(group -> TenantRole.TENANT_ADMIN.groupName().equals(group.getName()))) {
            return TenantRole.TENANT_ADMIN;
        }
        if (groups.stream().anyMatch(group -> TenantRole.MEMBER.groupName().equals(group.getName()))) {
            return TenantRole.MEMBER;
        }
        return null;
    }

    public boolean isTenantAdmin(OrganizationModel organization, UserModel user) {
        return roleOf(organization, user) == TenantRole.TENANT_ADMIN;
    }

    public Map<String, Object> tenantToMap(OrganizationModel organization, TenantRole role) {
        Map<String, Object> result = new LinkedHashMap<>();
        String tenantType = attribute(organization, TENANT_TYPE, TYPE_ENTERPRISE);
        String lifecycleStatus = attribute(organization, TENANT_STATUS, null);
        if (lifecycleStatus == null) {
            lifecycleStatus = TYPE_ENTERPRISE.equals(tenantType) && activeAdminCount(organization) == 0
                    ? STATUS_PENDING : STATUS_ACTIVE;
        }
        result.put("id", stableTenantId(organization));
        result.put("keycloak_org_id", organization.getId());
        result.put("alias", organization.getAlias());
        result.put("name", organization.getName());
        result.put("tenant_type", tenantType);
        result.put("lifecycle_status", lifecycleStatus);
        result.put("enabled", organization.isEnabled());
        result.put("protected", Boolean.parseBoolean(attribute(organization, TENANT_PROTECTED, "false")));
        result.put("role", role == null ? null : role.apiValue());
        return result;
    }

    private Map<String, Object> memberToMap(OrganizationModel organization, UserModel user) {
        TenantRole role = roleOf(organization, user);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", ensureStableUserId(user));
        result.put("keycloak_subject", user.getId());
        result.put("username", user.getUsername());
        result.put("email", user.getEmail());
        result.put("email_verified", user.isEmailVerified());
        result.put("enabled", user.isEnabled());
        result.put("active", role != null);
        result.put("role", role == null ? null : role.apiValue());
        result.put("owner", ensureStableUserId(user).equals(attribute(organization, TENANT_OWNER_ID, null)));
        return result;
    }

    private Map<String, Object> invitationToMap(OrganizationInvitationModel invitation) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("invitation_id", invitation.getId());
        result.put("email", invitation.getEmail());
        result.put("status", invitation.getStatus().name().toLowerCase());
        result.put("expires_at", Instant.ofEpochSecond(invitation.getExpiresAt()).toString());
        result.put("pending_registration", true);
        return result;
    }

    private OrganizationInvitationModel createInvitation(
            OrganizationModel organization, String email, TenantRole role) {
        InvitationManager manager = organizations.getInvitationManager();
        OrganizationInvitationModel existing = manager.getByEmail(organization, email);
        if (existing != null && !existing.isExpired()) {
            setAttribute(organization, INVITATION_ROLE_PREFIX + existing.getId(), role.apiValue());
            emit("iam.invitation.updated.v1", existing.getId(), Map.of(
                    "tenant_id", stableTenantId(organization),
                    "action", "role_updated",
                    "role", role.apiValue()));
            return existing;
        }
        if (existing != null) {
            manager.remove(existing.getId());
            removeAttribute(organization, INVITATION_ROLE_PREFIX + existing.getId());
            emit("iam.invitation.expired.v1", existing.getId(), Map.of(
                    "tenant_id", stableTenantId(organization)));
        }
        OrganizationInvitationModel invitation = manager.create(organization, email, null, null);
        invitation.setExpiresAt((int) Instant.now().getEpochSecond() + DEFAULT_INVITATION_TTL_SECONDS);
        setAttribute(organization, INVITATION_ROLE_PREFIX + invitation.getId(), role.apiValue());
        emit("iam.invitation.created.v1", invitation.getId(), Map.of(
                "tenant_id", stableTenantId(organization),
                "role", role.apiValue()));
        return invitation;
    }

    private void acceptPendingInvitations(UserModel user) {
        if (user.getEmail() == null || user.getEmail().isBlank()) {
            return;
        }
        InvitationManager manager = organizations.getInvitationManager();
        for (OrganizationModel organization : organizations.getAllStream().toList()) {
            OrganizationInvitationModel invitation = manager.getByEmail(organization, user.getEmail());
            if (invitation == null || invitation.isExpired()) {
                continue;
            }
            TenantRole role = TenantRole.fromApiValue(attribute(
                    organization, INVITATION_ROLE_PREFIX + invitation.getId(), TenantRole.MEMBER.apiValue()));
            if (assignRole(organization, user, role)) {
                emitMembership("iam.membership.created.v1", organization, user, role);
            }
            if (invitation.getId().equals(attribute(organization, INITIAL_ADMIN_INVITATION_ID, null))) {
                setAttribute(organization, TENANT_STATUS, STATUS_ACTIVE);
                removeAttribute(organization, INITIAL_ADMIN_INVITATION_ID);
            }
            removeAttribute(organization, INVITATION_ROLE_PREFIX + invitation.getId());
            manager.remove(invitation.getId());
            emit("iam.invitation.updated.v1", invitation.getId(), Map.of(
                    "tenant_id", stableTenantId(organization),
                    "action", "accepted"));
        }
    }

    private boolean assignRole(OrganizationModel organization, UserModel user, TenantRole role) {
        TenantRole currentRole = roleOf(organization, user);
        if (currentRole == role) {
            return false;
        }
        if (!organizations.isMember(organization, user)) {
            organizations.addMember(organization, user);
        }
        leaveMembershipGroups(organization, user);
        user.joinGroup(roleGroup(organization, role));
        return true;
    }

    private void deactivateMember(
            OrganizationModel organization, UserModel user, TenantRole currentRole) {
        if (currentRole == null && isMembershipDisabled(organization, user)) {
            return;
        }
        if (currentRole == TenantRole.TENANT_ADMIN && activeAdminCount(organization) <= 1) {
            throw new IamApiException(409, "last_tenant_admin", "不能移除最后一名租户管理员");
        }
        leaveMembershipGroups(organization, user);
        user.joinGroup(group(organization, GROUP_DISABLED, null));
        emitMembership("iam.membership.disabled.v1", organization, user, null);
    }

    private void leaveMembershipGroups(OrganizationModel organization, UserModel user) {
        organizations.getOrganizationGroupsByMember(organization, user)
                .filter(group -> GROUP_DISABLED.equals(group.getName())
                        || TenantRole.TENANT_ADMIN.groupName().equals(group.getName())
                        || TenantRole.MEMBER.groupName().equals(group.getName()))
                .toList()
                .forEach(user::leaveGroup);
    }

    private boolean isMembershipDisabled(OrganizationModel organization, UserModel user) {
        return organizations.getOrganizationGroupsByMember(organization, user)
                .anyMatch(group -> GROUP_DISABLED.equals(group.getName()));
    }

    private GroupModel roleGroup(OrganizationModel organization, TenantRole role) {
        RoleModel realmRole = realm.getRole(role.apiValue());
        if (realmRole == null) {
            throw new IamApiException(500, "role_configuration_error", "Realm 固定角色缺失");
        }
        return group(organization, role.groupName(), realmRole);
    }

    private GroupModel group(OrganizationModel organization, String name, RoleModel role) {
        GroupModel group = organizations.getTopLevelGroups(organization, null, null)
                .filter(candidate -> name.equals(candidate.getName()))
                .findFirst()
                .orElseGet(() -> organizations.createGroup(organization, name, null));
        if (role != null && !group.hasDirectRole(role)) {
            group.grantRole(role);
        }
        return group;
    }

    private long activeAdminCount(OrganizationModel organization) {
        return organizations.getMembersStream(organization, Map.of(), null, null, null)
                .filter(UserModel::isEnabled)
                .filter(user -> roleOf(organization, user) == TenantRole.TENANT_ADMIN)
                .count();
    }

    private OrganizationInvitationModel requireInvitation(String invitationId) {
        String expected = requireText(invitationId, "invitation_id", 128);
        OrganizationInvitationModel invitation = organizations.getInvitationManager().getById(expected);
        if (invitation == null) {
            throw new IamApiException(404, "invitation_not_found", "邀请不存在");
        }
        return invitation;
    }

    private UserModel findUser(String identifier) {
        UserModel byUsername = session.users().getUserByUsername(realm, identifier);
        UserModel byEmail = session.users().getUserByEmail(realm, identifier);
        if (byUsername != null && byEmail != null && !byUsername.getId().equals(byEmail.getId())) {
            throw new IamApiException(409, "ambiguous_identifier", "用户名和邮箱匹配到不同用户");
        }
        return byUsername != null ? byUsername : byEmail;
    }

    private void requireHumanUser(UserModel user) {
        if (user.getServiceAccountClientLink() != null) {
            throw new IamApiException(409, "service_account_forbidden", "服务账号不能加入业务租户");
        }
    }

    private UserModel requireMemberUser(OrganizationModel organization, String globalUserId) {
        String expected = requireText(globalUserId, "user_id", 64);
        return organizations.getMembersStream(organization, Map.of(), null, null, null)
                .filter(user -> expected.equals(user.getFirstAttribute(USER_GLOBAL_ID)))
                .findFirst()
                .orElseThrow(() -> new IamApiException(404, "membership_not_found", "租户成员不存在"));
    }

    private void requireEnterprise(OrganizationModel organization) {
        if (!TYPE_ENTERPRISE.equals(attribute(organization, TENANT_TYPE, null))) {
            throw new IamApiException(409, "personal_tenant_immutable", "个人空间不能执行成员或企业租户管理操作");
        }
    }

    private void requireActiveTenant(OrganizationModel organization) {
        if (!organization.isEnabled() || !STATUS_ACTIVE.equals(attribute(organization, TENANT_STATUS, null))) {
            throw new IamApiException(409, "tenant_inactive", "租户当前不可用");
        }
    }

    private String requireText(String value, String field, int maxLength) {
        if (value == null || value.isBlank()) {
            throw new IamApiException(400, "validation_error", field + " 不能为空");
        }
        String normalized = value.trim();
        if (normalized.length() > maxLength) {
            throw new IamApiException(400, "validation_error", field + " 长度不能超过 " + maxLength);
        }
        return normalized;
    }

    private String attribute(OrganizationModel organization, String name, String defaultValue) {
        List<String> values = organization.getAttributes().get(name);
        return values == null || values.isEmpty() ? defaultValue : values.getFirst();
    }

    private void setAttribute(OrganizationModel organization, String name, String value) {
        Map<String, List<String>> attributes = new HashMap<>(organization.getAttributes());
        attributes.put(name, List.of(value));
        organization.setAttributes(attributes);
    }

    private void removeAttribute(OrganizationModel organization, String name) {
        Map<String, List<String>> attributes = new HashMap<>(organization.getAttributes());
        attributes.remove(name);
        organization.setAttributes(attributes);
    }

    private String stableTenantId(OrganizationModel organization) {
        String stableId = attribute(organization, TENANT_GLOBAL_ID, null);
        if (stableId != null) {
            return stableId;
        }
        String alias = organization.getAlias();
        if (alias != null && (alias.startsWith("personal-") || alias.startsWith("enterprise-"))) {
            return alias.substring(alias.indexOf('-') + 1);
        }
        return organization.getId();
    }

    private void emitMembership(
            String eventType, OrganizationModel organization, UserModel user, TenantRole role) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("tenant_id", stableTenantId(organization));
        data.put("user_id", ensureStableUserId(user));
        if (role != null) {
            data.put("role", role.apiValue());
        }
        data.put("active", role != null);
        emit(eventType, stableTenantId(organization) + ":" + ensureStableUserId(user), data);
    }

    private void emit(String eventType, String aggregateId, Map<String, Object> data) {
        if (publisher != null) {
            publisher.publishAfterCommit(session, eventType, aggregateId, data);
        }
    }
}

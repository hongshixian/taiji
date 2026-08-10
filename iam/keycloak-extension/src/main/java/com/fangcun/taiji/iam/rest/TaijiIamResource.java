package com.fangcun.taiji.iam.rest;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.function.Supplier;
import java.util.stream.Collectors;

import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.DELETE;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.PATCH;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.PUT;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.jboss.logging.Logger;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.OrganizationModel;
import org.keycloak.models.RoleModel;
import org.keycloak.models.UserModel;
import org.keycloak.services.managers.AppAuthManager;
import org.keycloak.services.managers.AuthenticationManager;

import com.fangcun.taiji.iam.domain.IamApiException;
import com.fangcun.taiji.iam.domain.IdentityProvisioningService;
import com.fangcun.taiji.iam.domain.TenantRole;
import com.fangcun.taiji.iam.events.IamEventPublisher;

@Path("")
@Produces(MediaType.APPLICATION_JSON)
public final class TaijiIamResource {
    private static final Logger LOG = Logger.getLogger(TaijiIamResource.class);
    private static final String PLATFORM_ADMIN = "platform_admin";

    private final KeycloakSession session;
    private final IamEventPublisher publisher;
    private final Set<String> allowedClients;

    public TaijiIamResource(KeycloakSession session) {
        this.session = session;
        this.publisher = IamEventPublisher.shared();
        this.allowedClients = Arrays.stream(System.getenv()
                        .getOrDefault("TAIJI_IAM_ALLOWED_CLIENTS", "taiji-web,taiji-reconciler")
                        .split(","))
                .map(String::trim)
                .filter(value -> !value.isEmpty())
                .collect(Collectors.toUnmodifiableSet());
    }

    @GET
    @Path("health")
    public Response health() {
        return Response.ok(Map.of(
                "status", "ok",
                "provider", TaijiIamRealmResourceProviderFactory.PROVIDER_ID,
                "realm", session.getContext().getRealm().getName()
        )).build();
    }

    @GET
    @Path("v1/me/tenants")
    public Response myTenants() {
        return execute(() -> {
            UserModel actor = requireActor();
            IdentityProvisioningService service = service();
            RoleModel platformRole = session.getContext().getRealm().getRole(PLATFORM_ADMIN);
            return Response.ok(Map.of(
                    "user_id", service.ensureStableUserId(actor),
                    "platform_admin", platformRole != null && actor.hasRole(platformRole),
                    "tenants", service.listUserTenants(actor)
            )).build();
        });
    }

    @GET
    @Path("v1/platform-admins")
    public Response listPlatformAdmins() {
        return execute(() -> {
            requirePlatformAdmin();
            return Response.ok(Map.of("platform_admins", service().listPlatformAdmins())).build();
        });
    }

    @POST
    @Path("v1/platform-admins")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response grantPlatformAdmin(GrantPlatformAdminRequest request) {
        return execute(() -> {
            requirePlatformAdmin();
            if (request == null) {
                throw new IamApiException(400, "empty_body", "请求体不能为空");
            }
            return Response.ok(service().grantPlatformAdmin(request.identifier())).build();
        });
    }

    @DELETE
    @Path("v1/platform-admins/{userId}")
    public Response revokePlatformAdmin(@PathParam("userId") String userId) {
        return execute(() -> {
            UserModel actor = requirePlatformAdmin();
            return Response.ok(service().revokePlatformAdmin(userId, actor)).build();
        });
    }

    @POST
    @Path("v1/tenants")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response createTenant(
            @HeaderParam("Idempotency-Key") String idempotencyKey,
            CreateTenantRequest request) {
        return execute(() -> {
            UserModel actor = requirePlatformAdmin();
            if (request == null) {
                throw new IamApiException(400, "empty_body", "请求体不能为空");
            }
            IdentityProvisioningService service = service();
            OrganizationModel tenant = service.createEnterpriseTenant(
                    request.name(),
                    request.initialAdmin(),
                    idempotencyKey,
                    service.ensureStableUserId(actor));
            return Response.status(Response.Status.CREATED)
                    .entity(service.tenantToMap(tenant, null))
                    .build();
        });
    }

    @PATCH
    @Path("v1/tenants/{tenantId}")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response updateTenant(
            @PathParam("tenantId") String tenantId, UpdateTenantRequest request) {
        return execute(() -> {
            requirePlatformAdmin();
            if (request == null) {
                throw new IamApiException(400, "empty_body", "请求体不能为空");
            }
            IdentityProvisioningService service = service();
            OrganizationModel tenant = service.updateEnterpriseTenant(
                    tenantId, request.name(), request.enabled());
            return Response.ok(service.tenantToMap(tenant, null)).build();
        });
    }

    @GET
    @Path("v1/tenants/{tenantId}/members")
    public Response listMembers(@PathParam("tenantId") String tenantId) {
        return execute(() -> {
            IdentityProvisioningService service = service();
            OrganizationModel tenant = service.requireTenant(tenantId);
            requireTenantAdmin(service, tenant);
            return Response.ok(Map.of("members", service.listMembers(tenantId))).build();
        });
    }

    @POST
    @Path("v1/tenants/{tenantId}/members")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response addMember(
            @PathParam("tenantId") String tenantId, AddMemberRequest request) {
        return execute(() -> {
            IdentityProvisioningService service = service();
            OrganizationModel tenant = service.requireTenant(tenantId);
            requireTenantAdmin(service, tenant);
            if (request == null) {
                throw new IamApiException(400, "empty_body", "请求体不能为空");
            }
            Map<String, Object> result = service.addMember(
                    tenantId, request.identifier(), TenantRole.fromApiValue(request.role()));
            Response.Status status = result.containsKey("invitation_id")
                    ? Response.Status.ACCEPTED : Response.Status.CREATED;
            return Response.status(status).entity(result).build();
        });
    }

    @PATCH
    @Path("v1/tenants/{tenantId}/members/{userId}")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response updateMember(
            @PathParam("tenantId") String tenantId,
            @PathParam("userId") String userId,
            UpdateMemberRequest request) {
        return execute(() -> {
            IdentityProvisioningService service = service();
            OrganizationModel tenant = service.requireTenant(tenantId);
            requireTenantAdmin(service, tenant);
            if (request == null) {
                throw new IamApiException(400, "empty_body", "请求体不能为空");
            }
            TenantRole role = request.role() == null ? null : TenantRole.fromApiValue(request.role());
            return Response.ok(service.updateMember(tenantId, userId, role, request.active())).build();
        });
    }

    @DELETE
    @Path("v1/tenants/{tenantId}/members/{userId}")
    public Response deactivateMember(
            @PathParam("tenantId") String tenantId,
            @PathParam("userId") String userId) {
        return execute(() -> {
            IdentityProvisioningService service = service();
            OrganizationModel tenant = service.requireTenant(tenantId);
            requireTenantAdmin(service, tenant);
            return Response.ok(service.deactivateMember(tenantId, userId)).build();
        });
    }

    @POST
    @Path("v1/invitations/{invitationId}/resend")
    public Response resendInvitation(@PathParam("invitationId") String invitationId) {
        return execute(() -> {
            IdentityProvisioningService service = service();
            OrganizationModel tenant = service.tenantForInvitation(invitationId);
            requireTenantAdmin(service, tenant);
            return Response.ok(service.resendInvitation(invitationId)).build();
        });
    }

    @DELETE
    @Path("v1/invitations/{invitationId}")
    public Response revokeInvitation(@PathParam("invitationId") String invitationId) {
        return execute(() -> {
            IdentityProvisioningService service = service();
            OrganizationModel tenant = service.tenantForInvitation(invitationId);
            requireTenantAdmin(service, tenant);
            service.revokeInvitation(invitationId);
            return Response.noContent().build();
        });
    }

    @PUT
    @Path("v1/migration/users/{userId}")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response migrateUser(
            @PathParam("userId") String userId, MigrateUserRequest request) {
        return execute(() -> {
            requireMigrator();
            if (request == null) {
                throw new IamApiException(400, "empty_body", "请求体不能为空");
            }
            return Response.ok(service().migrateUser(
                    userId,
                    request.username(),
                    request.email(),
                    request.enabled(),
                    request.platformAdmin(),
                    request.linkExisting(),
                    request.legacyPasswordHash())).build();
        });
    }

    @PUT
    @Path("v1/migration/tenants/{tenantId}")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response migrateTenant(
            @PathParam("tenantId") String tenantId, MigrateTenantRequest request) {
        return execute(() -> {
            requireMigrator();
            if (request == null) {
                throw new IamApiException(400, "empty_body", "请求体不能为空");
            }
            return Response.ok(service().migrateEnterpriseTenant(
                    tenantId,
                    request.name(),
                    request.enabled(),
                    request.protectedTenant())).build();
        });
    }

    @PUT
    @Path("v1/migration/tenants/{tenantId}/members/{userId}")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response migrateMembership(
            @PathParam("tenantId") String tenantId,
            @PathParam("userId") String userId,
            MigrateMembershipRequest request) {
        return execute(() -> {
            requireMigrator();
            if (request == null) {
                throw new IamApiException(400, "empty_body", "请求体不能为空");
            }
            return Response.ok(service().migrateMembership(
                    tenantId,
                    userId,
                    TenantRole.fromApiValue(request.role()),
                    request.active())).build();
        });
    }

    private IdentityProvisioningService service() {
        return new IdentityProvisioningService(session, publisher);
    }

    private UserModel requireActor() {
        AuthenticationManager.AuthResult auth = authenticate();
        if (auth == null || auth.user() == null || auth.client() == null) {
            throw new IamApiException(401, "unauthorized", "需要有效 Bearer Token");
        }
        if (!allowedClients.contains(auth.client().getClientId())) {
            throw new IamApiException(403, "client_forbidden", "该 OIDC Client 无权调用此接口");
        }
        if (!auth.user().isEnabled()) {
            throw new IamApiException(403, "account_disabled", "账号已停用");
        }
        return auth.user();
    }

    private void requireMigrator() {
        if (!Boolean.parseBoolean(System.getenv().getOrDefault("IAM_MIGRATION_ENABLED", "false"))) {
            throw new IamApiException(404, "migration_disabled", "迁移端点未启用");
        }
        AuthenticationManager.AuthResult auth = authenticate();
        if (!"taiji-migrator".equals(auth.client().getClientId())
                || auth.user().getServiceAccountClientLink() == null
                || !auth.client().getId().equals(auth.user().getServiceAccountClientLink())) {
            throw new IamApiException(403, "migrator_required", "只允许专用迁移服务账号调用");
        }
    }

    private AuthenticationManager.AuthResult authenticate() {
        AuthenticationManager.AuthResult auth =
                new AppAuthManager.BearerTokenAuthenticator(session).authenticate();
        if (auth == null || auth.user() == null || auth.client() == null) {
            throw new IamApiException(401, "unauthorized", "需要有效 Bearer Token");
        }
        return auth;
    }

    private UserModel requirePlatformAdmin() {
        UserModel actor = requireActor();
        RoleModel role = session.getContext().getRealm().getRole(PLATFORM_ADMIN);
        if (role == null || !actor.hasRole(role)) {
            throw new IamApiException(403, "platform_admin_required", "需要平台超级管理员权限");
        }
        return actor;
    }

    private UserModel requireTenantAdmin(
            IdentityProvisioningService service, OrganizationModel tenant) {
        UserModel actor = requireActor();
        RoleModel platformRole = session.getContext().getRealm().getRole(PLATFORM_ADMIN);
        if (platformRole != null && actor.hasRole(platformRole)) {
            return actor;
        }
        if (!service.isTenantAdmin(tenant, actor)) {
            throw new IamApiException(403, "tenant_admin_required", "需要租户管理员权限");
        }
        return actor;
    }

    private Response execute(Supplier<Response> action) {
        try {
            return action.get();
        } catch (IamApiException error) {
            return error(error.status(), error.code(), error.getMessage());
        } catch (RuntimeException error) {
            LOG.error("Unexpected IAM REST error", error);
            return error(500, "internal_error", "IAM 服务处理请求失败");
        }
    }

    private Response error(int status, String code, String message) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("code", code);
        body.put("message", message);
        return Response.status(status).entity(body).build();
    }

    public record CreateTenantRequest(String name, String initialAdmin) {
    }

    public record UpdateTenantRequest(String name, Boolean enabled) {
    }

    public record AddMemberRequest(String identifier, String role) {
    }

    public record UpdateMemberRequest(String role, Boolean active) {
    }

    public record MigrateUserRequest(
            String username,
            String email,
            boolean enabled,
            boolean platformAdmin,
            boolean linkExisting,
            String legacyPasswordHash) {
    }

    public record MigrateTenantRequest(String name, boolean enabled, boolean protectedTenant) {
    }

    public record MigrateMembershipRequest(String role, boolean active) {
    }

    public record GrantPlatformAdminRequest(String identifier) {
    }
}

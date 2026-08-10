package com.fangcun.taiji.iam.events;

import org.jboss.logging.Logger;
import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventType;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.UserModel;

import com.fangcun.taiji.iam.domain.IdentityProvisioningService;

public final class TaijiIamEventListenerProvider implements EventListenerProvider {
    private static final Logger LOG = Logger.getLogger(TaijiIamEventListenerProvider.class);

    private final KeycloakSession session;
    private final IamEventPublisher publisher;

    public TaijiIamEventListenerProvider(KeycloakSession session, IamEventPublisher publisher) {
        this.session = session;
        this.publisher = publisher;
    }

    @Override
    public void onEvent(Event event) {
        LOG.debugf("IAM user event type=%s realm=%s user=%s", event.getType(), event.getRealmId(), event.getUserId());
        if (event.getUserId() == null || !provisionsIdentity(event.getType())) {
            return;
        }

        UserModel user = session.users().getUserById(session.getContext().getRealm(), event.getUserId());
        if (user == null || user.getServiceAccountClientLink() != null) {
            return;
        }

        IdentityProvisioningService service = new IdentityProvisioningService(session, publisher);
        service.provisionRegisteredUser(user);
        publisher.publishAfterCommit(
                session,
                event.getType() == EventType.REGISTER ? "iam.user.created.v1" : "iam.user.updated.v1",
                service.ensureStableUserId(user),
                java.util.Map.of("enabled", user.isEnabled()));
    }

    @Override
    public void onEvent(AdminEvent event, boolean includeRepresentation) {
        LOG.debugf("IAM admin event operation=%s resource=%s", event.getOperationType(), event.getResourcePath());
    }

    @Override
    public void close() {
    }

    private boolean provisionsIdentity(EventType type) {
        return type == EventType.REGISTER
                || type == EventType.LOGIN
                || type == EventType.IDENTITY_PROVIDER_FIRST_LOGIN;
    }
}

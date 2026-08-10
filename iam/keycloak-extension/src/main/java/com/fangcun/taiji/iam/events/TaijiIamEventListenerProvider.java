package com.fangcun.taiji.iam.events;

import org.jboss.logging.Logger;
import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.admin.AdminEvent;

public final class TaijiIamEventListenerProvider implements EventListenerProvider {
    private static final Logger LOG = Logger.getLogger(TaijiIamEventListenerProvider.class);

    @Override
    public void onEvent(Event event) {
        LOG.debugf("IAM user event type=%s realm=%s user=%s", event.getType(), event.getRealmId(), event.getUserId());
    }

    @Override
    public void onEvent(AdminEvent event, boolean includeRepresentation) {
        LOG.debugf("IAM admin event operation=%s resource=%s", event.getOperationType(), event.getResourcePath());
    }

    @Override
    public void close() {
    }
}

package com.fangcun.taiji.iam.events;

import org.keycloak.Config;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventListenerProviderFactory;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;

public final class TaijiIamEventListenerProviderFactory implements EventListenerProviderFactory {
    public static final String PROVIDER_ID = "taiji-iam-events";
    private final IamEventPublisher publisher = IamEventPublisher.shared();

    @Override
    public EventListenerProvider create(KeycloakSession session) {
        return new TaijiIamEventListenerProvider(session, publisher);
    }

    @Override
    public void init(Config.Scope config) {
    }

    @Override
    public void postInit(KeycloakSessionFactory factory) {
    }

    @Override
    public void close() {
        publisher.close();
    }

    @Override
    public String getId() {
        return PROVIDER_ID;
    }
}

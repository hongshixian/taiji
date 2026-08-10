package com.fangcun.taiji.iam.rest;

import org.keycloak.models.KeycloakSession;
import org.keycloak.services.resource.RealmResourceProvider;

public final class TaijiIamRealmResourceProvider implements RealmResourceProvider {
    private final KeycloakSession session;

    public TaijiIamRealmResourceProvider(KeycloakSession session) {
        this.session = session;
    }

    @Override
    public Object getResource() {
        return new TaijiIamResource(session);
    }

    @Override
    public void close() {
    }
}

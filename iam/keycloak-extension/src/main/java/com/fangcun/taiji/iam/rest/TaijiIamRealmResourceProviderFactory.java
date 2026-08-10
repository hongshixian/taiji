package com.fangcun.taiji.iam.rest;

import org.keycloak.Config;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.services.resource.RealmResourceProvider;
import org.keycloak.services.resource.RealmResourceProviderFactory;

public final class TaijiIamRealmResourceProviderFactory implements RealmResourceProviderFactory {
    public static final String PROVIDER_ID = "taiji-iam";

    @Override
    public RealmResourceProvider create(KeycloakSession session) {
        return new TaijiIamRealmResourceProvider(session);
    }

    @Override
    public void init(Config.Scope config) {
    }

    @Override
    public void postInit(KeycloakSessionFactory factory) {
    }

    @Override
    public void close() {
    }

    @Override
    public String getId() {
        return PROVIDER_ID;
    }
}

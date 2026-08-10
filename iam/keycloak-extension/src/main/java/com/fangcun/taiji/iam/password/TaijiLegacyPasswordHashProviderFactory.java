package com.fangcun.taiji.iam.password;

import org.keycloak.Config;
import org.keycloak.credential.hash.PasswordHashProvider;
import org.keycloak.credential.hash.PasswordHashProviderFactory;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;

public final class TaijiLegacyPasswordHashProviderFactory implements PasswordHashProviderFactory {
    @Override
    public PasswordHashProvider create(KeycloakSession session) {
        return new TaijiLegacyPasswordHashProvider();
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
        return TaijiLegacyPasswordHashProvider.ID;
    }

    @Override
    public int order() {
        return -100;
    }
}

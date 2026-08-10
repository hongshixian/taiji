package com.fangcun.taiji.iam.rest;

import java.util.Map;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.Provider;
import org.keycloak.models.KeycloakSession;

@Provider
@Path("")
public final class TaijiIamResource {
    private final KeycloakSession session;

    public TaijiIamResource(KeycloakSession session) {
        this.session = session;
    }

    @GET
    @Path("health")
    @Produces(MediaType.APPLICATION_JSON)
    public Response health() {
        return Response.ok(Map.of(
                "status", "ok",
                "provider", TaijiIamRealmResourceProviderFactory.PROVIDER_ID,
                "realm", session.getContext().getRealm().getName()
        )).build();
    }
}

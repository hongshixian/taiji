package com.fangcun.taiji.iam.events;

import java.io.IOException;
import java.time.Duration;
import java.util.Map;

import io.nats.client.Connection;
import io.nats.client.JetStream;
import io.nats.client.JetStreamApiException;
import io.nats.client.JetStreamManagement;
import io.nats.client.Nats;
import io.nats.client.Options;
import io.nats.client.api.StorageType;
import io.nats.client.api.StreamConfiguration;
import io.nats.client.impl.Headers;
import org.jboss.logging.Logger;
import org.keycloak.models.AbstractKeycloakTransaction;
import org.keycloak.models.KeycloakSession;
import org.keycloak.util.JsonSerialization;

public final class IamEventPublisher implements AutoCloseable {
    private static final Logger LOG = Logger.getLogger(IamEventPublisher.class);
    private static final String STREAM_NAME = "IAM_EVENTS";
    private static final int MAX_ATTEMPTS = 3;

    private final String natsUrl;
    private volatile Connection connection;

    private static final class Holder {
        private static final IamEventPublisher INSTANCE = new IamEventPublisher();
    }

    public static IamEventPublisher shared() {
        return Holder.INSTANCE;
    }

    public IamEventPublisher() {
        this.natsUrl = System.getenv().getOrDefault("NATS_URL", "nats://localhost:4222");
    }

    public void publishAfterCommit(
            KeycloakSession session,
            String eventType,
            String aggregateId,
            Map<String, Object> data) {
        IamEventEnvelope envelope = IamEventEnvelope.create(
                eventType,
                session.getContext().getRealm().getName(),
                aggregateId,
                data);
        session.getTransactionManager().enlistAfterCompletion(new AbstractKeycloakTransaction() {
            @Override
            protected void commitImpl() {
                publishWithRetry(envelope);
            }

            @Override
            protected void rollbackImpl() {
                // A rolled-back IAM mutation must not reach consumers.
            }
        });
    }

    void publishWithRetry(IamEventEnvelope envelope) {
        RuntimeException lastFailure = null;
        for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            try {
                byte[] payload = JsonSerialization.writeValueAsBytes(envelope.asMap());
                Headers headers = new Headers();
                headers.put("Nats-Msg-Id", envelope.eventId());
                jetStream().publish(envelope.subject(), headers, payload);
                return;
            } catch (IOException | JetStreamApiException | RuntimeException error) {
                lastFailure = error instanceof RuntimeException runtime
                        ? runtime : new IllegalStateException(error);
                resetConnection();
                if (attempt < MAX_ATTEMPTS) {
                    sleep(attempt);
                }
            }
        }
        LOG.errorf(lastFailure,
                "Unable to publish IAM event after %d attempts eventId=%s type=%s aggregate=%s",
                MAX_ATTEMPTS,
                envelope.eventId(),
                envelope.eventType(),
                envelope.aggregateId());
    }

    private JetStream jetStream() throws IOException, JetStreamApiException {
        Connection active;
        try {
            active = connection();
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new IOException("Interrupted while connecting to NATS", interrupted);
        }
        ensureStream(active);
        return active.jetStream();
    }

    private synchronized Connection connection() throws IOException, InterruptedException {
        if (connection == null || connection.getStatus() == Connection.Status.CLOSED) {
            Options options = new Options.Builder()
                    .server(natsUrl)
                    .connectionName("taiji-keycloak-iam-events")
                    .connectionTimeout(Duration.ofSeconds(2))
                    .maxReconnects(2)
                    .build();
            connection = Nats.connect(options);
        }
        return connection;
    }

    private void ensureStream(Connection active) throws IOException, JetStreamApiException {
        JetStreamManagement management = active.jetStreamManagement();
        try {
            management.getStreamInfo(STREAM_NAME);
        } catch (JetStreamApiException error) {
            if (error.getErrorCode() != 404) {
                throw error;
            }
            try {
                management.addStream(StreamConfiguration.builder()
                        .name(STREAM_NAME)
                        .subjects("iam.>")
                        .storageType(StorageType.File)
                        .build());
            } catch (JetStreamApiException concurrentCreate) {
                if (concurrentCreate.getErrorCode() != 400) {
                    throw concurrentCreate;
                }
                management.getStreamInfo(STREAM_NAME);
            }
        }
    }

    private void sleep(int attempt) {
        try {
            Thread.sleep(100L * attempt);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
        }
    }

    private synchronized void resetConnection() {
        if (connection != null) {
            try {
                connection.close();
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
            } finally {
                connection = null;
            }
        }
    }

    @Override
    public void close() {
        resetConnection();
    }
}

package com.fangcun.taiji.iam.events;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

public record IamEventEnvelope(
        String eventId,
        String eventType,
        Instant occurredAt,
        String realm,
        String aggregateId,
        long aggregateVersion,
        Map<String, Object> data) {

    public static IamEventEnvelope create(
            String eventType, String realm, String aggregateId, Map<String, Object> data) {
        Instant occurredAt = Instant.now();
        return new IamEventEnvelope(
                UUID.randomUUID().toString(),
                eventType,
                occurredAt,
                realm,
                aggregateId,
                occurredAt.toEpochMilli(),
                Map.copyOf(data));
    }

    public String subject() {
        return eventType;
    }

    public Map<String, Object> asMap() {
        return Map.of(
                "event_id", eventId,
                "event_type", eventType,
                "occurred_at", occurredAt.toString(),
                "realm", realm,
                "aggregate_id", aggregateId,
                "aggregate_version", aggregateVersion,
                "data", data);
    }
}

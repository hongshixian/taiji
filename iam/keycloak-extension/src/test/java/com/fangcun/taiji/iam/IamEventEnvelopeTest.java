package com.fangcun.taiji.iam;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import java.util.Map;

import com.fangcun.taiji.iam.events.IamEventEnvelope;
import org.junit.jupiter.api.Test;

class IamEventEnvelopeTest {
    @Test
    void createsVersionedSubjectAndDefensiveDataCopy() {
        IamEventEnvelope event = IamEventEnvelope.create(
                "iam.tenant.created.v1", "fangcun", "tenant-1", Map.of("type", "enterprise"));

        assertEquals("iam.tenant.created.v1", event.subject());
        assertEquals("fangcun", event.realm());
        assertEquals("tenant-1", event.aggregateId());
        assertEquals("enterprise", event.data().get("type"));
        assertEquals("iam.tenant.created.v1", event.asMap().get("event_type"));
        assertEquals("tenant-1", event.asMap().get("aggregate_id"));
        assertFalse(event.eventId().isBlank());
        assertEquals(event.occurredAt().toEpochMilli(), event.aggregateVersion());
    }
}

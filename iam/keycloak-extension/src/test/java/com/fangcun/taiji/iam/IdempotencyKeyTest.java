package com.fangcun.taiji.iam;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.UUID;

import com.fangcun.taiji.iam.domain.IamApiException;
import com.fangcun.taiji.iam.domain.IdempotencyKey;
import org.junit.jupiter.api.Test;

class IdempotencyKeyTest {
    @Test
    void createsStableScopedUuid() {
        String first = IdempotencyKey.deterministicUuid("actor:create", "request-1");
        assertEquals(first, IdempotencyKey.deterministicUuid("actor:create", "request-1"));
        assertNotEquals(first, IdempotencyKey.deterministicUuid("other:create", "request-1"));
        assertEquals(36, first.length());
        assertEquals(5, UUID.fromString(first).version());
    }

    @Test
    void rejectsMissingAndOversizedKeys() {
        assertThrows(IamApiException.class, () -> IdempotencyKey.deterministicUuid("scope", null));
        assertThrows(IamApiException.class, () -> IdempotencyKey.deterministicUuid("scope", "x".repeat(129)));
    }
}

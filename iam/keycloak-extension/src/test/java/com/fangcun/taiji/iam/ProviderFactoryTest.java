package com.fangcun.taiji.iam;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.fangcun.taiji.iam.events.TaijiIamEventListenerProviderFactory;
import com.fangcun.taiji.iam.rest.TaijiIamRealmResourceProviderFactory;
import org.junit.jupiter.api.Test;

class ProviderFactoryTest {
    @Test
    void providerIdsRemainStable() {
        assertEquals("taiji-iam", new TaijiIamRealmResourceProviderFactory().getId());
        assertEquals("taiji-iam-events", new TaijiIamEventListenerProviderFactory().getId());
    }
}

package com.fangcun.taiji.iam.domain;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.UUID;

public final class IdempotencyKey {
    private IdempotencyKey() {
    }

    public static String deterministicUuid(String scope, String key) {
        byte[] digest = sha256Bytes(scope + "\u0000" + requireKey(key));
        digest[6] = (byte) ((digest[6] & 0x0f) | 0x50);
        digest[8] = (byte) ((digest[8] & 0x3f) | 0x80);
        ByteBuffer bytes = ByteBuffer.wrap(digest);
        return new UUID(bytes.getLong(), bytes.getLong()).toString();
    }

    public static String fingerprint(String... values) {
        return sha256(String.join("\u0000", values));
    }

    private static String requireKey(String key) {
        if (key == null || key.isBlank()) {
            throw new IamApiException(400, "idempotency_key_required", "缺少 Idempotency-Key 请求头");
        }
        String normalized = key.trim();
        if (normalized.length() > 128) {
            throw new IamApiException(400, "idempotency_key_invalid", "Idempotency-Key 长度不能超过 128");
        }
        return normalized;
    }

    private static String sha256(String value) {
        return HexFormat.of().formatHex(sha256Bytes(value));
    }

    private static byte[] sha256Bytes(String value) {
        try {
            return MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 unavailable", impossible);
        }
    }
}

package com.fangcun.taiji.iam.password;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.spec.InvalidKeySpecException;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

import org.bouncycastle.crypto.generators.SCrypt;
import org.keycloak.credential.hash.PasswordHashProvider;
import org.keycloak.models.PasswordPolicy;
import org.keycloak.models.credential.PasswordCredentialModel;

/** Validates Werkzeug hashes only long enough for Keycloak to rehash them. */
public final class TaijiLegacyPasswordHashProvider implements PasswordHashProvider {
    public static final String ID = "taiji-legacy";

    @Override
    public boolean policyCheck(PasswordPolicy policy, PasswordCredentialModel credential) {
        return false;
    }

    @Override
    public PasswordCredentialModel encodedCredential(String rawPassword, int iterations) {
        throw new UnsupportedOperationException("taiji-legacy is validation-only");
    }

    @Override
    public boolean verify(String rawPassword, PasswordCredentialModel credential) {
        if (rawPassword == null || credential == null || credential.getPasswordSecretData() == null) {
            return false;
        }
        String encoded = credential.getPasswordSecretData().getValue();
        if (!isSupportedFormat(encoded)) {
            return false;
        }
        try {
            String[] parts = encoded.split("\\$", -1);
            if (parts.length != 3) {
                return false;
            }
            byte[] expected = decodeHex(parts[2]);
            byte[] actual;
            if (parts[0].startsWith("scrypt:")) {
                actual = verifyScrypt(rawPassword, parts[0], parts[1], expected.length);
            } else if (parts[0].startsWith("pbkdf2:")) {
                actual = verifyPbkdf2(rawPassword, parts[0], parts[1], expected.length);
            } else {
                return false;
            }
            return MessageDigest.isEqual(expected, actual);
        } catch (IllegalArgumentException | NoSuchAlgorithmException | InvalidKeySpecException error) {
            return false;
        }
    }

    @Override
    public String credentialHashingStrength(PasswordCredentialModel credential) {
        String value = credential.getPasswordSecretData().getValue();
        int separator = value == null ? -1 : value.indexOf('$');
        return separator > 0 ? value.substring(0, separator) : ID;
    }

    @Override
    public void close() {
    }

    public static boolean isSupportedFormat(String encoded) {
        if (encoded == null || encoded.length() > 1024) {
            return false;
        }
        try {
            String[] parts = encoded.split("\\$", -1);
            if (parts.length != 3 || parts[1].isEmpty()) {
                return false;
            }
            int length = decodeHex(parts[2]).length;
            if (length < 16 || length > 128) {
                return false;
            }
            if (parts[0].startsWith("scrypt:")) {
                String[] params = parts[0].split(":", -1);
                if (params.length != 4) {
                    return false;
                }
                int n = parseBounded(params[1], 2, 131_072);
                int r = parseBounded(params[2], 1, 16);
                int p = parseBounded(params[3], 1, 4);
                return (n & (n - 1)) == 0 && (long) n * r <= 1_048_576;
            }
            if (parts[0].startsWith("pbkdf2:")) {
                String[] params = parts[0].split(":", -1);
                if (params.length != 3
                        || !("sha1".equals(params[1])
                        || "sha256".equals(params[1])
                        || "sha512".equals(params[1]))) {
                    return false;
                }
                parseBounded(params[2], 1, 2_000_000);
                return true;
            }
            return false;
        } catch (IllegalArgumentException error) {
            return false;
        }
    }

    private static byte[] verifyScrypt(String password, String method, String salt, int length) {
        String[] params = method.split(":", -1);
        if (params.length != 4) {
            throw new IllegalArgumentException("invalid scrypt method");
        }
        int n = parseBounded(params[1], 2, 131_072);
        int r = parseBounded(params[2], 1, 16);
        int p = parseBounded(params[3], 1, 4);
        if ((n & (n - 1)) != 0 || (long) n * r > 1_048_576
                || length < 16 || length > 128) {
            throw new IllegalArgumentException("unsafe scrypt parameters");
        }
        return SCrypt.generate(
                password.getBytes(StandardCharsets.UTF_8),
                salt.getBytes(StandardCharsets.UTF_8),
                n,
                r,
                p,
                length
        );
    }

    private static byte[] verifyPbkdf2(String password, String method, String salt, int length)
            throws NoSuchAlgorithmException, InvalidKeySpecException {
        String[] params = method.split(":", -1);
        if (params.length != 3 || length < 16 || length > 128) {
            throw new IllegalArgumentException("invalid PBKDF2 method");
        }
        String digest = switch (params[1]) {
            case "sha1" -> "PBKDF2WithHmacSHA1";
            case "sha256" -> "PBKDF2WithHmacSHA256";
            case "sha512" -> "PBKDF2WithHmacSHA512";
            default -> throw new IllegalArgumentException("unsupported PBKDF2 digest");
        };
        int iterations = parseBounded(params[2], 1, 2_000_000);
        PBEKeySpec spec = new PBEKeySpec(
                password.toCharArray(),
                salt.getBytes(StandardCharsets.UTF_8),
                iterations,
                length * 8
        );
        try {
            return SecretKeyFactory.getInstance(digest).generateSecret(spec).getEncoded();
        } finally {
            spec.clearPassword();
        }
    }

    private static int parseBounded(String value, int minimum, int maximum) {
        int parsed = Integer.parseInt(value);
        if (parsed < minimum || parsed > maximum) {
            throw new IllegalArgumentException("parameter outside allowed range");
        }
        return parsed;
    }

    private static byte[] decodeHex(String value) {
        if (value.length() % 2 != 0) {
            throw new IllegalArgumentException("invalid hex length");
        }
        byte[] result = new byte[value.length() / 2];
        for (int index = 0; index < result.length; index++) {
            int high = Character.digit(value.charAt(index * 2), 16);
            int low = Character.digit(value.charAt(index * 2 + 1), 16);
            if (high < 0 || low < 0) {
                throw new IllegalArgumentException("invalid hex value");
            }
            result[index] = (byte) ((high << 4) | low);
        }
        return result;
    }
}

package com.fangcun.taiji.iam;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fangcun.taiji.iam.password.TaijiLegacyPasswordHashProvider;
import com.fangcun.taiji.iam.password.TaijiLegacyPasswordHashProviderFactory;
import org.junit.jupiter.api.Test;
import org.keycloak.models.credential.PasswordCredentialModel;

class LegacyPasswordHashProviderTest {
    private static final String SCRYPT = "scrypt:32768:8:1$ffpn1fRbzS2oh0HT$"
            + "4021e1132568b96d9ff73a88cb54ba0455ec0ad8088a13651f13154680f3e32c"
            + "f484bc54742bd13487e8d714b08ad3bd94bfea0324780f26380a126a64e10da8";
    private static final String PBKDF2 = "pbkdf2:sha256:600000$SsavuSxWXp0wlXZf$"
            + "b1dcf60b99336810eb9004793d016ffdbc83f0db3292aeddaeb942e4728eafc5";

    private final TaijiLegacyPasswordHashProvider provider =
            new TaijiLegacyPasswordHashProvider();

    @Test
    void verifiesWerkzeugScryptAndRejectsWrongPassword() {
        assertTrue(provider.verify("CorrectHorse1!", credential(SCRYPT)));
        assertFalse(provider.verify("wrong", credential(SCRYPT)));
    }

    @Test
    void verifiesWerkzeugPbkdf2AndRejectsWrongPassword() {
        assertTrue(provider.verify("CorrectHorse1!", credential(PBKDF2)));
        assertFalse(provider.verify("wrong", credential(PBKDF2)));
    }

    @Test
    void rejectsMalformedOrExpensiveCredentials() {
        assertFalse(provider.verify("value", credential("plain$value$value")));
        assertFalse(provider.verify("value", credential("scrypt:1073741824:8:1$salt$0011")));
        assertFalse(provider.verify("value", credential("pbkdf2:sha256:999999999$salt$0011")));
        assertFalse(provider.verify("value", credential("scrypt:32768:8:1$salt$not-hex")));
        assertFalse(TaijiLegacyPasswordHashProvider.isSupportedFormat(
                "scrypt:131072:16:1$salt$00112233445566778899aabbccddeeff"));
    }

    @Test
    void isValidationOnlyAndAlwaysRequestsRehash() {
        assertFalse(provider.policyCheck(null, credential(SCRYPT)));
        assertThrows(
                UnsupportedOperationException.class,
                () -> provider.encodedCredential("password", 1)
        );
        assertTrue(new TaijiLegacyPasswordHashProviderFactory().order() < 0);
    }

    private static PasswordCredentialModel credential(String encoded) {
        return PasswordCredentialModel.createFromValues(
                TaijiLegacyPasswordHashProvider.ID,
                new byte[0],
                0,
                encoded
        );
    }
}

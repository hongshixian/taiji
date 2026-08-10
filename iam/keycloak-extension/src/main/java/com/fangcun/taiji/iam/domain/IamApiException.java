package com.fangcun.taiji.iam.domain;

public final class IamApiException extends RuntimeException {
    private final int status;
    private final String code;

    public IamApiException(int status, String code, String message) {
        super(message);
        this.status = status;
        this.code = code;
    }

    public int status() {
        return status;
    }

    public String code() {
        return code;
    }
}

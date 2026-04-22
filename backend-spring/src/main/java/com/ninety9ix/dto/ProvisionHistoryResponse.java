package com.ninety9ix.dto;

import java.time.Instant;

public record ProvisionHistoryResponse(
        Long id,
        Long accessRequestId,
        Long userId,
        String issuedBy,
        Instant issuedAt,
        String message
) {
}

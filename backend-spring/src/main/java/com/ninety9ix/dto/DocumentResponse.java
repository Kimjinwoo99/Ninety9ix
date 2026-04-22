package com.ninety9ix.dto;

import com.ninety9ix.domain.DocumentStatus;
import com.ninety9ix.domain.DocumentType;

import java.time.Instant;

public record DocumentResponse(
        Long id,
        String sessionId,
        DocumentType type,
        String fileName,
        String fileUrl,
        String storagePath,
        DocumentStatus status,
        Instant uploadedAt
) {
}

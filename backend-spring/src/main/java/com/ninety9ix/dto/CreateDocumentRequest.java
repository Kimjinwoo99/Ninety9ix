package com.ninety9ix.dto;

import com.ninety9ix.domain.DocumentStatus;
import com.ninety9ix.domain.DocumentType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record CreateDocumentRequest(
        @NotNull DocumentType type,
        @NotBlank String fileName,
        String fileUrl,
        String storagePath,
        DocumentStatus status
) {
}

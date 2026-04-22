package com.ninety9ix.dto;

import com.ninety9ix.domain.AccessRequestStatus;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record ReviewAccessRequestRequest(
        @NotNull AccessRequestStatus status,
        @Size(max = 255) String reviewNote
) {
}

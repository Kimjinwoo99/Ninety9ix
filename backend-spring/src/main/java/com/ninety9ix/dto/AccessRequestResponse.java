package com.ninety9ix.dto;

import com.ninety9ix.domain.AccessRequestStatus;
import com.ninety9ix.domain.UserRole;

import java.time.Instant;

public record AccessRequestResponse(
        Long id,
        String name,
        String employeeNumber,
        String department,
        UserRole requestedRole,
        AccessRequestStatus status,
        String reviewNote,
        String reviewedBy,
        Instant createdAt,
        Instant reviewedAt
) {
}

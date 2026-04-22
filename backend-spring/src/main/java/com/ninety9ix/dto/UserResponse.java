package com.ninety9ix.dto;

import com.ninety9ix.domain.UserRole;

import java.time.Instant;

public record UserResponse(
        Long id,
        String username,
        String name,
        String employeeNumber,
        String department,
        UserRole role,
        Boolean superAdmin,
        Boolean enabled,
        Instant createdAt
) {
}

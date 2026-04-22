package com.ninety9ix.dto;

import com.ninety9ix.domain.CustomerStatus;

import java.time.Instant;
import java.time.LocalDate;

public record CustomerResponse(
        String id,
        String name,
        String phone,
        String email,
        String address,
        LocalDate birthDate,
        Instant registeredAt,
        CustomerStatus status
) {
}

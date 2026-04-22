package com.ninety9ix.dto;

import com.ninety9ix.domain.CustomerStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.time.Instant;
import java.time.LocalDate;

public record CreateCustomerRequest(
        @Size(max = 64) String id,
        @NotBlank @Size(max = 255) String name,
        @Size(max = 50) String phone,
        @Size(max = 255) String email,
        @Size(max = 500) String address,
        LocalDate birthDate,
        Instant registeredAt,
        CustomerStatus status
) {
}

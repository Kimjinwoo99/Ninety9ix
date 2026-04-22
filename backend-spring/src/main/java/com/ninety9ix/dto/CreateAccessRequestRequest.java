package com.ninety9ix.dto;

import com.ninety9ix.domain.UserRole;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record CreateAccessRequestRequest(
        @NotBlank @Size(max = 100) String name,
        @NotBlank
        @Size(max = 50)
        @Pattern(regexp = "^[a-zA-Z0-9-]+$", message = "사원번호 형식이 올바르지 않습니다.")
        String employeeNumber,
        @NotBlank @Size(max = 100) String department,
        @NotNull UserRole requestedRole
) {
}

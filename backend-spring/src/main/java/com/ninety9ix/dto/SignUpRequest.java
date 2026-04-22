package com.ninety9ix.dto;

import com.ninety9ix.domain.UserRole;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record SignUpRequest(
        @NotBlank
        @Size(min = 4, max = 50)
        @Pattern(regexp = "^[a-zA-Z0-9._-]+$", message = "아이디는 영문/숫자/._- 만 사용 가능합니다.")
        String username,
        @NotBlank
        @Size(min = 8, max = 100)
        String password,
        @NotBlank
        @Size(max = 100)
        String name,
        @Size(max = 50)
        String employeeNumber,
        @Size(max = 100)
        String department,
        @NotNull
        UserRole role
) {
}

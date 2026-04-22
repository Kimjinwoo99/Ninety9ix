package com.ninety9ix.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record ProvisionFromRequestRequest(
        @NotNull Long requestId,
        @NotBlank
        @Size(min = 4, max = 50)
        @Pattern(regexp = "^[a-zA-Z0-9._-]+$", message = "아이디는 영문/숫자/._- 만 사용 가능합니다.")
        String username,
        @NotBlank
        @Size(min = 8, max = 100)
        String password
) {
}

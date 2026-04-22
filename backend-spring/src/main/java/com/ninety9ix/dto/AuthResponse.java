package com.ninety9ix.dto;

public record AuthResponse(
        String token,
        String tokenType,
        UserResponse user
) {
}

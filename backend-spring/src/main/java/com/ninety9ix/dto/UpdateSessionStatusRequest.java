package com.ninety9ix.dto;

import com.ninety9ix.domain.SessionStatus;
import jakarta.validation.constraints.NotNull;

public record UpdateSessionStatusRequest(@NotNull SessionStatus status) {
}

package com.ninety9ix.dto;

import com.ninety9ix.domain.SessionStatus;

import java.time.Instant;

public record SessionResponse(String id, SessionStatus status, Instant createdAt, Instant completedAt) {
}

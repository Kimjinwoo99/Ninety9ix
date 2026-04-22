package com.ninety9ix.dto;

import com.ninety9ix.domain.SessionStatus;

public record CreateSessionRequest(SessionStatus status) {
}

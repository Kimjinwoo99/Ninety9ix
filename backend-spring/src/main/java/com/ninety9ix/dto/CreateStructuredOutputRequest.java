package com.ninety9ix.dto;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.NotNull;

public record CreateStructuredOutputRequest(Long documentId, @NotNull JsonNode payload) {
}

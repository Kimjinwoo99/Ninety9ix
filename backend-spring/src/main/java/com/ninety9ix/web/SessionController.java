package com.ninety9ix.web;

import com.ninety9ix.dto.CreateDocumentRequest;
import com.ninety9ix.dto.CreateSessionRequest;
import com.ninety9ix.dto.CreateStructuredOutputRequest;
import com.ninety9ix.dto.DocumentResponse;
import com.ninety9ix.dto.SessionResponse;
import com.ninety9ix.dto.UpdateSessionStatusRequest;
import com.ninety9ix.service.RegistrationSessionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/sessions")
@RequiredArgsConstructor
@PreAuthorize("hasAnyRole('SYSTEM_ADMIN','STAFF')")
public class SessionController {

    private final RegistrationSessionService registrationSessionService;

    @PostMapping
    public SessionResponse create(@RequestBody(required = false) CreateSessionRequest request) {
        return registrationSessionService.createSession(request);
    }

    @GetMapping("/{id}")
    public SessionResponse get(@PathVariable String id) {
        return registrationSessionService.getSession(id);
    }

    @PatchMapping("/{id}/status")
    public SessionResponse updateStatus(@PathVariable String id, @Valid @RequestBody UpdateSessionStatusRequest request) {
        return registrationSessionService.updateStatus(id, request.status());
    }

    @PostMapping("/{sessionId}/documents")
    public DocumentResponse addDocument(@PathVariable String sessionId, @Valid @RequestBody CreateDocumentRequest request) {
        return registrationSessionService.addDocument(sessionId, request);
    }

    @GetMapping("/{sessionId}/documents")
    public List<DocumentResponse> listDocuments(@PathVariable String sessionId) {
        return registrationSessionService.listDocuments(sessionId);
    }

    @PostMapping("/{sessionId}/structured-output")
    public ResponseEntity<Void> saveStructuredOutput(
            @PathVariable String sessionId,
            @Valid @RequestBody CreateStructuredOutputRequest request
    ) {
        registrationSessionService.saveStructuredOutput(sessionId, request);
        return ResponseEntity.noContent().build();
    }

    @GetMapping(value = "/{sessionId}/structured-output/latest", produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<String> latestStructuredOutput(@PathVariable String sessionId) {
        String json = registrationSessionService.getLatestStructuredOutputJson(sessionId);
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON).body(json);
    }
}

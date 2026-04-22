package com.ninety9ix.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ninety9ix.domain.Document;
import com.ninety9ix.domain.RegistrationSession;
import com.ninety9ix.domain.SessionStatus;
import com.ninety9ix.domain.StructuredOutputSnapshot;
import com.ninety9ix.dto.CreateDocumentRequest;
import com.ninety9ix.dto.CreateSessionRequest;
import com.ninety9ix.dto.CreateStructuredOutputRequest;
import com.ninety9ix.dto.DocumentResponse;
import com.ninety9ix.dto.SessionResponse;
import com.ninety9ix.repository.DocumentRepository;
import com.ninety9ix.repository.RegistrationSessionRepository;
import com.ninety9ix.repository.StructuredOutputSnapshotRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;

@Service
@RequiredArgsConstructor
public class RegistrationSessionService {

    private final RegistrationSessionRepository sessionRepository;
    private final DocumentRepository documentRepository;
    private final StructuredOutputSnapshotRepository snapshotRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public SessionResponse createSession(CreateSessionRequest request) {
        RegistrationSession session = new RegistrationSession();
        if (request != null && request.status() != null) {
            session.setStatus(request.status());
        }
        sessionRepository.save(session);
        return toSessionResponse(session);
    }

    @Transactional(readOnly = true)
    public SessionResponse getSession(String id) {
        return sessionRepository.findById(id)
                .map(this::toSessionResponse)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "세션을 찾을 수 없습니다."));
    }

    @Transactional
    public SessionResponse updateStatus(String id, SessionStatus status) {
        RegistrationSession session = sessionRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "세션을 찾을 수 없습니다."));
        session.setStatus(status);
        if (status == SessionStatus.completed || status == SessionStatus.cancelled) {
            session.setCompletedAt(Instant.now());
        }
        sessionRepository.save(session);
        return toSessionResponse(session);
    }

    @Transactional
    public DocumentResponse addDocument(String sessionId, CreateDocumentRequest request) {
        RegistrationSession session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "세션을 찾을 수 없습니다."));
        Document doc = new Document();
        doc.setSession(session);
        doc.setType(request.type());
        doc.setFileName(request.fileName());
        doc.setFileUrl(request.fileUrl());
        doc.setStoragePath(request.storagePath());
        if (request.status() != null) {
            doc.setStatus(request.status());
        }
        documentRepository.save(doc);
        return toDocumentResponse(doc);
    }

    @Transactional(readOnly = true)
    public List<DocumentResponse> listDocuments(String sessionId) {
        if (!sessionRepository.existsById(sessionId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "세션을 찾을 수 없습니다.");
        }
        return documentRepository.findBySession_IdOrderByUploadedAtDesc(sessionId).stream()
                .map(this::toDocumentResponse)
                .toList();
    }

    @Transactional
    public void saveStructuredOutput(String sessionId, CreateStructuredOutputRequest request) {
        RegistrationSession session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "세션을 찾을 수 없습니다."));
        Document document = null;
        if (request.documentId() != null) {
            document = documentRepository.findById(request.documentId())
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "문서를 찾을 수 없습니다."));
            if (!document.getSession().getId().equals(sessionId)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "문서가 해당 세션에 속하지 않습니다.");
            }
        }
        String json;
        try {
            json = objectMapper.writeValueAsString(request.payload());
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "JSON 직렬화 실패");
        }
        StructuredOutputSnapshot snap = new StructuredOutputSnapshot();
        snap.setSession(session);
        snap.setDocument(document);
        snap.setPayloadJson(json);
        snapshotRepository.save(snap);
    }

    @Transactional(readOnly = true)
    public String getLatestStructuredOutputJson(String sessionId) {
        if (!sessionRepository.existsById(sessionId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "세션을 찾을 수 없습니다.");
        }
        return snapshotRepository.findFirstBySession_IdOrderByCreatedAtDesc(sessionId)
                .map(StructuredOutputSnapshot::getPayloadJson)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "저장된 structured output이 없습니다."));
    }

    private SessionResponse toSessionResponse(RegistrationSession s) {
        return new SessionResponse(s.getId(), s.getStatus(), s.getCreatedAt(), s.getCompletedAt());
    }

    private DocumentResponse toDocumentResponse(Document d) {
        return new DocumentResponse(
                d.getId(),
                d.getSession().getId(),
                d.getType(),
                d.getFileName(),
                d.getFileUrl(),
                d.getStoragePath(),
                d.getStatus(),
                d.getUploadedAt()
        );
    }
}

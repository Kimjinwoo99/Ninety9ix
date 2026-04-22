package com.ninety9ix.repository;

import com.ninety9ix.domain.Document;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DocumentRepository extends JpaRepository<Document, Long> {
    List<Document> findBySession_IdOrderByUploadedAtDesc(String sessionId);
}

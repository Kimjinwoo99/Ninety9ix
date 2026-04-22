package com.ninety9ix.repository;

import com.ninety9ix.domain.StructuredOutputSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface StructuredOutputSnapshotRepository extends JpaRepository<StructuredOutputSnapshot, Long> {
    List<StructuredOutputSnapshot> findBySession_IdOrderByCreatedAtDesc(String sessionId);

    Optional<StructuredOutputSnapshot> findFirstBySession_IdOrderByCreatedAtDesc(String sessionId);
}

package com.ninety9ix.repository;

import com.ninety9ix.domain.AccessRequest;
import com.ninety9ix.domain.AccessRequestStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AccessRequestRepository extends JpaRepository<AccessRequest, Long> {
    boolean existsByEmployeeNumber(String employeeNumber);

    List<AccessRequest> findAllByOrderByCreatedAtDesc();

    List<AccessRequest> findByStatusOrderByCreatedAtDesc(AccessRequestStatus status);
}

package com.ninety9ix.service;

import com.ninety9ix.domain.AccessRequest;
import com.ninety9ix.domain.AccessRequestStatus;
import com.ninety9ix.dto.AccessRequestResponse;
import com.ninety9ix.dto.CreateAccessRequestRequest;
import com.ninety9ix.dto.ReviewAccessRequestRequest;
import com.ninety9ix.repository.AccessRequestRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;

@Service
@RequiredArgsConstructor
public class AccessRequestService {

    private final AccessRequestRepository accessRequestRepository;

    @Transactional
    public AccessRequestResponse create(CreateAccessRequestRequest request) {
        if (accessRequestRepository.existsByEmployeeNumber(request.employeeNumber())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 요청된 사원번호입니다.");
        }
        AccessRequest accessRequest = new AccessRequest();
        accessRequest.setName(request.name());
        accessRequest.setEmployeeNumber(request.employeeNumber());
        accessRequest.setDepartment(request.department());
        accessRequest.setRequestedRole(request.requestedRole());
        accessRequest.setStatus(AccessRequestStatus.PENDING);
        accessRequestRepository.save(accessRequest);
        return toResponse(accessRequest);
    }

    @Transactional(readOnly = true)
    public List<AccessRequestResponse> list(String status) {
        if (status == null || status.isBlank()) {
            return accessRequestRepository.findAllByOrderByCreatedAtDesc().stream().map(this::toResponse).toList();
        }
        AccessRequestStatus parsed;
        try {
            parsed = AccessRequestStatus.valueOf(status.trim().toUpperCase());
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "유효하지 않은 status 값입니다.");
        }
        return accessRequestRepository.findByStatusOrderByCreatedAtDesc(parsed).stream().map(this::toResponse).toList();
    }

    @Transactional
    public AccessRequestResponse review(Long id, ReviewAccessRequestRequest request, String reviewerUsername) {
        AccessRequest accessRequest = accessRequestRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "요청을 찾을 수 없습니다."));
        if (accessRequest.getStatus() != AccessRequestStatus.PENDING) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "이미 처리된 요청입니다.");
        }
        if (request.status() == AccessRequestStatus.PENDING) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "처리 상태는 REJECTED만 허용됩니다.");
        }
        if (request.status() == AccessRequestStatus.APPROVED) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "APPROVED는 계정 생성 API를 통해서만 처리할 수 있습니다.");
        }
        accessRequest.setStatus(request.status());
        accessRequest.setReviewNote(request.reviewNote());
        accessRequest.setReviewedBy(reviewerUsername);
        accessRequest.setReviewedAt(Instant.now());
        accessRequestRepository.save(accessRequest);
        return toResponse(accessRequest);
    }

    private AccessRequestResponse toResponse(AccessRequest accessRequest) {
        return new AccessRequestResponse(
                accessRequest.getId(),
                accessRequest.getName(),
                accessRequest.getEmployeeNumber(),
                accessRequest.getDepartment(),
                accessRequest.getRequestedRole(),
                accessRequest.getStatus(),
                accessRequest.getReviewNote(),
                accessRequest.getReviewedBy(),
                accessRequest.getCreatedAt(),
                accessRequest.getReviewedAt()
        );
    }
}

package com.ninety9ix.service;

import com.ninety9ix.domain.AccessRequest;
import com.ninety9ix.domain.AccessRequestStatus;
import com.ninety9ix.domain.AppUser;
import com.ninety9ix.domain.UserProvisionHistory;
import com.ninety9ix.dto.AuthResponse;
import com.ninety9ix.dto.LoginRequest;
import com.ninety9ix.dto.ProvisionFromRequestRequest;
import com.ninety9ix.dto.ProvisionHistoryResponse;
import com.ninety9ix.dto.SignUpRequest;
import com.ninety9ix.dto.UserResponse;
import com.ninety9ix.repository.AccessRequestRepository;
import com.ninety9ix.repository.AppUserRepository;
import com.ninety9ix.repository.UserProvisionHistoryRepository;
import com.ninety9ix.security.JwtTokenProvider;
import com.ninety9ix.security.UserPrincipal;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final AppUserRepository appUserRepository;
    private final AccessRequestRepository accessRequestRepository;
    private final UserProvisionHistoryRepository userProvisionHistoryRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuthenticationManager authenticationManager;
    private final JwtTokenProvider jwtTokenProvider;

    @Transactional
    public UserResponse signUp(SignUpRequest request) {
        if (appUserRepository.existsByUsername(request.username())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 사용 중인 아이디입니다.");
        }
        if (request.employeeNumber() != null
                && !request.employeeNumber().isBlank()
                && appUserRepository.existsByEmployeeNumber(request.employeeNumber())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 계정이 존재하는 사원번호입니다.");
        }
        AppUser user = new AppUser();
        user.setUsername(request.username());
        user.setPasswordHash(passwordEncoder.encode(request.password()));
        user.setName(request.name());
        user.setEmployeeNumber(request.employeeNumber());
        user.setDepartment(request.department());
        user.setRole(request.role());
        user.setEnabled(true);
        appUserRepository.save(user);
        return toResponse(user);
    }

    @Transactional(readOnly = true)
    public AuthResponse login(LoginRequest request) {
        Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.username(), request.password())
        );
        UserPrincipal principal = (UserPrincipal) authentication.getPrincipal();
        String token = jwtTokenProvider.generateToken(principal);
        return new AuthResponse(token, "Bearer", toResponse(principal));
    }

    @Transactional(readOnly = true)
    public UserResponse me(UserPrincipal principal) {
        return toResponse(principal);
    }

    @Transactional
    public UserResponse provisionFromAccessRequest(ProvisionFromRequestRequest request, String reviewerUsername) {
        if (appUserRepository.existsByUsername(request.username())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 사용 중인 아이디입니다.");
        }
        AccessRequest accessRequest = accessRequestRepository.findById(request.requestId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "요청을 찾을 수 없습니다."));
        if (accessRequest.getEmployeeNumber() != null
                && !accessRequest.getEmployeeNumber().isBlank()
                && appUserRepository.existsByEmployeeNumber(accessRequest.getEmployeeNumber())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 계정이 존재하는 사원번호입니다.");
        }
        if (accessRequest.getStatus() != AccessRequestStatus.PENDING) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "PENDING 상태 요청만 계정 생성할 수 있습니다.");
        }
        AppUser user = new AppUser();
        user.setUsername(request.username());
        user.setPasswordHash(passwordEncoder.encode(request.password()));
        user.setName(accessRequest.getName());
        user.setEmployeeNumber(accessRequest.getEmployeeNumber());
        user.setDepartment(accessRequest.getDepartment());
        user.setRole(accessRequest.getRequestedRole());
        user.setEnabled(true);
        appUserRepository.save(user);

        accessRequest.setStatus(AccessRequestStatus.APPROVED);
        accessRequest.setReviewNote("관리자 승인 및 계정 생성 완료");
        accessRequest.setReviewedBy(reviewerUsername);
        accessRequest.setReviewedAt(java.time.Instant.now());
        accessRequestRepository.save(accessRequest);

        UserProvisionHistory history = new UserProvisionHistory();
        history.setAccessRequestId(accessRequest.getId());
        history.setUserId(user.getId());
        history.setIssuedBy(reviewerUsername);
        history.setMessage("발급 완료");
        userProvisionHistoryRepository.save(history);

        return toResponse(user);
    }

    @Transactional(readOnly = true)
    public List<UserResponse> listUsers() {
        return appUserRepository.findAll().stream().map(this::toResponse).toList();
    }

    @Transactional
    public void deleteUser(Long userId, String requesterUsername) {
        AppUser requester = appUserRepository.findByUsername(requesterUsername)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "요청자 정보를 찾을 수 없습니다."));
        if (requester.getId().equals(userId)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "자기 자신 계정은 삭제할 수 없습니다.");
        }
        AppUser target = appUserRepository.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "삭제할 사용자를 찾을 수 없습니다."));
        if ("admin".equalsIgnoreCase(target.getUsername())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "최고 관리자 계정은 삭제할 수 없습니다.");
        }
        if (target.getRole() == com.ninety9ix.domain.UserRole.SYSTEM_ADMIN
                && !"admin".equalsIgnoreCase(requester.getUsername())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "다른 관리자 계정은 최고 관리자(admin)만 삭제할 수 있습니다.");
        }
        appUserRepository.deleteById(userId);
    }

    @Transactional(readOnly = true)
    public List<ProvisionHistoryResponse> listProvisionHistories() {
        return userProvisionHistoryRepository.findAllByOrderByIssuedAtDesc().stream()
                .map(h -> new ProvisionHistoryResponse(
                        h.getId(),
                        h.getAccessRequestId(),
                        h.getUserId(),
                        h.getIssuedBy(),
                        h.getIssuedAt(),
                        h.getMessage()
                ))
                .toList();
    }

    private UserResponse toResponse(AppUser user) {
        return new UserResponse(
                user.getId(),
                user.getUsername(),
                user.getName(),
                user.getEmployeeNumber(),
                user.getDepartment(),
                user.getRole(),
                "admin".equalsIgnoreCase(user.getUsername()),
                user.getEnabled(),
                user.getCreatedAt()
        );
    }

    private UserResponse toResponse(UserPrincipal principal) {
        return new UserResponse(
                principal.getId(),
                principal.getUsername(),
                principal.getName(),
                null,
                null,
                com.ninety9ix.domain.UserRole.valueOf(principal.getRole()),
                "admin".equalsIgnoreCase(principal.getUsername()),
                principal.isEnabled(),
                null
        );
    }
}

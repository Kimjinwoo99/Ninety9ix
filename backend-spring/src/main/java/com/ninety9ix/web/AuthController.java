package com.ninety9ix.web;

import com.ninety9ix.dto.AuthResponse;
import com.ninety9ix.dto.LoginRequest;
import com.ninety9ix.dto.ProvisionFromRequestRequest;
import com.ninety9ix.dto.ProvisionHistoryResponse;
import com.ninety9ix.dto.SignUpRequest;
import com.ninety9ix.dto.UserResponse;
import com.ninety9ix.security.UserPrincipal;
import com.ninety9ix.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public AuthResponse login(@Valid @RequestBody LoginRequest request) {
        return authService.login(request);
    }

    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    @PostMapping("/signup")
    public UserResponse signUp(@Valid @RequestBody SignUpRequest request) {
        return authService.signUp(request);
    }

    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    @PostMapping("/provision-from-request")
    public UserResponse provisionFromRequest(
            @Valid @RequestBody ProvisionFromRequestRequest request,
            @AuthenticationPrincipal UserPrincipal principal
    ) {
        return authService.provisionFromAccessRequest(request, principal.getUsername());
    }

    @GetMapping("/me")
    public UserResponse me(@AuthenticationPrincipal UserPrincipal principal) {
        return authService.me(principal);
    }

    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    @GetMapping("/users")
    public List<UserResponse> listUsers() {
        return authService.listUsers();
    }

    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    @DeleteMapping("/users/{id}")
    public void deleteUser(@PathVariable Long id, @AuthenticationPrincipal UserPrincipal principal) {
        authService.deleteUser(id, principal.getUsername());
    }

    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    @GetMapping("/provision-histories")
    public List<ProvisionHistoryResponse> listProvisionHistories() {
        return authService.listProvisionHistories();
    }
}

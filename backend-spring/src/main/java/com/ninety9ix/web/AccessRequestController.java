package com.ninety9ix.web;

import com.ninety9ix.dto.AccessRequestResponse;
import com.ninety9ix.dto.CreateAccessRequestRequest;
import com.ninety9ix.dto.ReviewAccessRequestRequest;
import com.ninety9ix.security.UserPrincipal;
import com.ninety9ix.service.AccessRequestService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/access-requests")
@RequiredArgsConstructor
public class AccessRequestController {

    private final AccessRequestService accessRequestService;

    @PostMapping
    public AccessRequestResponse create(@Valid @RequestBody CreateAccessRequestRequest request) {
        return accessRequestService.create(request);
    }

    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    @GetMapping
    public List<AccessRequestResponse> list(@RequestParam(required = false) String status) {
        return accessRequestService.list(status);
    }

    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    @PatchMapping("/{id}/review")
    public AccessRequestResponse review(
            @PathVariable Long id,
            @Valid @RequestBody ReviewAccessRequestRequest request,
            @AuthenticationPrincipal UserPrincipal principal
    ) {
        return accessRequestService.review(id, request, principal.getUsername());
    }
}

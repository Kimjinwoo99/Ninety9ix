package com.ninety9ix.web;

import com.ninety9ix.dto.CreateCustomerRequest;
import com.ninety9ix.dto.CustomerResponse;
import com.ninety9ix.service.CustomerService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/customers")
@RequiredArgsConstructor
@PreAuthorize("hasAnyRole('SYSTEM_ADMIN','STAFF')")
public class CustomerController {

    private final CustomerService customerService;

    @GetMapping
    public List<CustomerResponse> list() {
        return customerService.listCustomers();
    }

    @PostMapping
    public CustomerResponse create(@Valid @RequestBody CreateCustomerRequest request) {
        return customerService.createCustomer(request);
    }
}

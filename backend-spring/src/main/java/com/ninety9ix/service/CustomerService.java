package com.ninety9ix.service;

import com.ninety9ix.domain.Customer;
import com.ninety9ix.domain.CustomerStatus;
import com.ninety9ix.dto.CreateCustomerRequest;
import com.ninety9ix.dto.CustomerResponse;
import com.ninety9ix.repository.CustomerRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
@RequiredArgsConstructor
public class CustomerService {

    private final CustomerRepository customerRepository;

    @Transactional(readOnly = true)
    public List<CustomerResponse> listCustomers() {
        return customerRepository.findAll().stream().map(this::toResponse).toList();
    }

    @Transactional
    public CustomerResponse createCustomer(CreateCustomerRequest request) {
        if (request.id() != null && !request.id().isBlank() && customerRepository.existsById(request.id())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 존재하는 고객 ID입니다.");
        }
        Customer c = new Customer();
        if (request.id() != null && !request.id().isBlank()) {
            c.setId(request.id());
        }
        c.setName(request.name());
        c.setPhone(request.phone() != null ? request.phone() : "");
        c.setEmail(request.email());
        c.setAddress(request.address());
        c.setBirthDate(request.birthDate());
        if (request.registeredAt() != null) {
            c.setRegisteredAt(request.registeredAt());
        }
        if (request.status() != null) {
            c.setStatus(request.status());
        } else {
            c.setStatus(CustomerStatus.active);
        }
        customerRepository.save(c);
        return toResponse(c);
    }

    private CustomerResponse toResponse(Customer c) {
        return new CustomerResponse(
                c.getId(),
                c.getName(),
                c.getPhone(),
                c.getEmail(),
                c.getAddress(),
                c.getBirthDate(),
                c.getRegisteredAt(),
                c.getStatus()
        );
    }
}

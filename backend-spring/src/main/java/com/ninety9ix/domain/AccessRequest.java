package com.ninety9ix.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;

@Entity
@Table(name = "access_request")
@Getter
@Setter
@NoArgsConstructor
public class AccessRequest {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, unique = true, length = 50)
    private String employeeNumber;

    @Column(nullable = false, length = 100)
    private String department;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private UserRole requestedRole;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AccessRequestStatus status;

    @Column(length = 255)
    private String reviewNote;

    @Column(length = 100)
    private String reviewedBy;

    @Column(nullable = false)
    private Instant createdAt;

    private Instant reviewedAt;

    @PrePersist
    void prePersist() {
        if (status == null) {
            status = AccessRequestStatus.PENDING;
        }
        if (createdAt == null) {
            createdAt = Instant.now();
        }
    }
}

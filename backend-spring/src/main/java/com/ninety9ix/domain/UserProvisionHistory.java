package com.ninety9ix.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
@Table(name = "user_provision_history")
@Getter
@Setter
@NoArgsConstructor
public class UserProvisionHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long accessRequestId;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false, length = 50)
    private String issuedBy;

    @Column(nullable = false)
    private Instant issuedAt;

    @Column(nullable = false, length = 255)
    private String message;

    @PrePersist
    void prePersist() {
        if (issuedAt == null) {
            issuedAt = Instant.now();
        }
    }
}

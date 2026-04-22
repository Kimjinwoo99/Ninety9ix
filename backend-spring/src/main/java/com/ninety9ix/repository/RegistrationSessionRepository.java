package com.ninety9ix.repository;

import com.ninety9ix.domain.RegistrationSession;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RegistrationSessionRepository extends JpaRepository<RegistrationSession, String> {
}

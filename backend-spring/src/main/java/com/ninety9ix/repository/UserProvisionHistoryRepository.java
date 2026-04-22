package com.ninety9ix.repository;

import com.ninety9ix.domain.UserProvisionHistory;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface UserProvisionHistoryRepository extends JpaRepository<UserProvisionHistory, Long> {
    List<UserProvisionHistory> findAllByOrderByIssuedAtDesc();
}

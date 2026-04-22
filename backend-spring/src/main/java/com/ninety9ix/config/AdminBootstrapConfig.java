package com.ninety9ix.config;

import com.ninety9ix.domain.AppUser;
import com.ninety9ix.domain.UserRole;
import com.ninety9ix.repository.AppUserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.password.PasswordEncoder;

@Configuration
@RequiredArgsConstructor
public class AdminBootstrapConfig {

    private final AppUserRepository appUserRepository;
    private final PasswordEncoder passwordEncoder;

    @Bean
    public CommandLineRunner adminBootstrapRunner(
            @Value("${app.security.seed-admin.username:admin}") String adminUsername,
            @Value("${app.security.seed-admin.password:Admin1234!}") String adminPassword,
            @Value("${app.security.seed-admin.name:System Admin}") String adminName
    ) {
        return args -> {
            if (appUserRepository.count() > 0) {
                return;
            }
            AppUser admin = new AppUser();
            admin.setUsername(adminUsername);
            admin.setPasswordHash(passwordEncoder.encode(adminPassword));
            admin.setName(adminName);
            admin.setEmployeeNumber("ADMIN-0001");
            admin.setDepartment("SYSTEM");
            admin.setRole(UserRole.SYSTEM_ADMIN);
            admin.setEnabled(true);
            appUserRepository.save(admin);
        };
    }
}

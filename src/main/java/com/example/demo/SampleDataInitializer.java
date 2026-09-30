package com.example.demo;

import com.example.demo.entity.Category;
import com.example.demo.entity.Customer;
import com.example.demo.repository.CategoryRepository;
import com.example.demo.repository.CustomerRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class SampleDataInitializer implements CommandLineRunner {

    private final CategoryRepository categoryRepository;
    private final CustomerRepository customerRepository;

    public SampleDataInitializer(
            CategoryRepository categoryRepository,
            CustomerRepository customerRepository) {
        this.categoryRepository = categoryRepository;
        this.customerRepository = customerRepository;
    }

    @Override
    public void run(String... args) {
        seedCategory("Electronics", "Computers, accessories, and devices");
        seedCategory("Office", "Supplies for home and office work");
        seedCategory("Home", "Useful products for everyday living");

        seedCustomer("Ava", "Martin", "ava.martin@example.com");
        seedCustomer("Noah", "Wilson", "noah.wilson@example.com");
        seedCustomer("Mia", "Chen", "mia.chen@example.com");
    }

    private void seedCategory(String name, String description) {
        if (!categoryRepository.existsByName(name)) {
            categoryRepository.save(new Category(name, description));
        }
    }

    private void seedCustomer(String firstName, String lastName, String email) {
        if (!customerRepository.existsByEmail(email)) {
            customerRepository.save(new Customer(firstName, lastName, email));
        }
    }
}
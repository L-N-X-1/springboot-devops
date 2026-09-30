package com.example.demo.service;

import com.example.demo.entity.Customer;
import java.util.List;

public interface CustomerService {

    List<Customer> findAll();

    Customer findById(Long id);

    Customer create(Customer customer);

    Customer update(Long id, Customer customer);

    void delete(Long id);
}
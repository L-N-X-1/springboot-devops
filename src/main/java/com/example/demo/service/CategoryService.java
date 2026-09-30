package com.example.demo.service;

import com.example.demo.entity.Category;
import java.util.List;

public interface CategoryService {

    List<Category> findAll();

    Category findById(Long id);

    Category create(Category category);

    Category update(Long id, Category category);

    void delete(Long id);
}
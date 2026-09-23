package com.example.demo.dto;

public class ProductResponse {

    private final Long id;
    private final String name;
    private final double price;

    public ProductResponse(Long id, String name, double price) {
        this.id = id;
        this.name = name;
        this.price = price;
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public double getPrice() {
        return price;
    }
}
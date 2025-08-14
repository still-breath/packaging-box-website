package com.backendjava.storageapi.model;

/**
 * Merepresentasikan data satu jenis Box yang diterima dari frontend.
 */
public class Box {
    private String id;
    private int quantity;
    private double length;
    private double width;
    private double height;
    private double weight;
    private String group;

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public int getQuantity() { return quantity; }
    public void setQuantity(int quantity) { this.quantity = quantity; }
    public double getLength() { return length; }
    public void setLength(double length) { this.length = length; }
    public double getWidth() { return width; }
    public void setWidth(double width) { this.width = width; }
    public double getHeight() { return height; }
    public void setHeight(double height) { this.height = height; }
    public double getWeight() { return weight; }
    public void setWeight(double weight) { this.weight = weight; }
    public String getGroup() { return group; }
    public void setGroup(String group) { this.group = group; }
}

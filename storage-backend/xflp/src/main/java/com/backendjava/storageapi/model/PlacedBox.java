package com.backendjava.storageapi.model;

/**
 * Merepresentasikan satu Box yang berhasil ditempatkan, termasuk koordinatnya.
 * Ini adalah bagian dari respons yang akan dikirim ke frontend.
 */
public class PlacedBox {
    private String id;
    private double x, y, z;
    private double length, width, height;
    private double weight;
    private String color;

    // Getters and Setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public double getX() { return x; }
    public void setX(double x) { this.x = x; }
    public double getY() { return y; }
    public void setY(double y) { this.y = y; }
    public double getZ() { return z; }
    public void setZ(double z) { this.z = z; }
    public double getLength() { return length; }
    public void setLength(double length) { this.length = length; }
    public double getWidth() { return width; }
    public void setWidth(double width) { this.width = width; }
    public double getHeight() { return height; }
    public void setHeight(double height) { this.height = height; }
    public double getWeight() { return weight; }
    public void setWeight(double weight) { this.weight = weight; }
    public String getColor() { return color; }
    public void setColor(String color) { this.color = color; }
}

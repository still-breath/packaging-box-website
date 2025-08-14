package com.backendjava.storageapi.model;


public class Container {
    private double length;
    private double width;
    private double height;
    private double maxWeight;

    // Getters and Setters
    public double getLength() { return length; }
    public void setLength(double length) { this.length = length; }
    public double getWidth() { return width; }
    public void setWidth(double width) { this.width = width; }
    public double getHeight() { return height; }
    public void setHeight(double height) { this.height = height; }
    public double getMaxWeight() { return maxWeight; }
    public void setMaxWeight(double maxWeight) { this.maxWeight = maxWeight; }

    public double getVolume() {
        return this.length * this.width * this.height;
    }
    
    // Method setVolume() dihapus karena tidak lagi diperlukan.
}

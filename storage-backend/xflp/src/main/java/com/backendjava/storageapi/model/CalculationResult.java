package com.backendjava.storageapi.model;

import java.util.List;

/**
 * Merepresentasikan keseluruhan hasil kalkulasi yang akan dikirim ke frontend.
 * Ini adalah "kontrak API" untuk respons.
 */
public class CalculationResult {
    private double fillRate;
    private double totalWeight;
    private double containerVolume; // Properti baru ditambahkan
    private List<PlacedBox> placedItems;
    private List<Box> unplacedItems;

    // Getters and Setters
    public double getFillRate() { return fillRate; }
    public void setFillRate(double fillRate) { this.fillRate = fillRate; }
    public double getTotalWeight() { return totalWeight; }
    public void setTotalWeight(double totalWeight) { this.totalWeight = totalWeight; }
    public double getContainerVolume() { return containerVolume; }
    public void setContainerVolume(double containerVolume) { this.containerVolume = containerVolume; }
    public List<PlacedBox> getPlacedItems() { return placedItems; }
    public void setPlacedItems(List<PlacedBox> placedItems) { this.placedItems = placedItems; }
    public List<Box> getUnplacedItems() { return unplacedItems; }
    public void setUnplacedItems(List<Box> unplacedItems) { this.unplacedItems = unplacedItems; }
}

package com.backendjava.storageapi.model;

import java.util.List;

public class CalculationRequest {
    private Container container;
    private List<Box> items;
    private List<Group> groups; // Properti baru untuk menampung data grup

    // Getters and Setters
    public Container getContainer() { return container; }
    public void setContainer(Container container) { this.container = container; }
    public List<Box> getItems() { return items; }
    public void setItems(List<Box> items) { this.items = items; }
    public List<Group> getGroups() { return groups; }
    public void setGroups(List<Group> groups) { this.groups = groups; }
}

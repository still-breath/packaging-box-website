package com.backendjava.storageapi.adapter;

import com.backendjava.storageapi.model.CalculationResult;
import com.backendjava.storageapi.model.Container; // Impor Container
import com.backendjava.storageapi.model.PlacedBox;
import com.example.backend.XflpBackendService;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class XflpOutputAdapter {

    public static CalculationResult toCalculationResult(XflpBackendService.PackingResult rawResult, Container container) {
        CalculationResult result = new CalculationResult();
        List<PlacedBox> placedBoxes = new ArrayList<>();

        Pattern pattern = Pattern.compile("id=(.*?), x=(.*?), y=(.*?), z=(.*?), w=(.*?), l=(.*?), h=(.*?),");

        for (String itemString : rawResult.loadedItems) {
            Matcher matcher = pattern.matcher(itemString);
            if (matcher.find()) {
                PlacedBox box = new PlacedBox();
                box.setId(matcher.group(1).trim());
                box.setX(Double.parseDouble(matcher.group(2).trim()));
                box.setY(Double.parseDouble(matcher.group(3).trim()));
                box.setZ(Double.parseDouble(matcher.group(4).trim()));
                box.setWidth(Double.parseDouble(matcher.group(5).trim()));
                box.setLength(Double.parseDouble(matcher.group(6).trim()));
                box.setHeight(Double.parseDouble(matcher.group(7).trim()));
                box.setWeight(0);
                box.setColor("#A95E90");
                
                placedBoxes.add(box);
            }
        }

        result.setPlacedItems(placedBoxes);
        result.setFillRate(rawResult.volumeFillRate);
        
        double volume = container.getLength() * container.getWidth() * container.getHeight();
        result.setContainerVolume(volume);
        
        double totalWeight = placedBoxes.stream().mapToDouble(PlacedBox::getWeight).sum();
        result.setTotalWeight(totalWeight);
        result.setUnplacedItems(new ArrayList<>());

        return result;
    }
}

package com.backendjava.storageapi.controller;

import com.backendjava.storageapi.model.*; // Impor semua model
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import xf.xflp.XFLP;
import xf.xflp.opt.XFLPOptType;
import xf.xflp.opt.construction.strategy.Strategy;
import xf.xflp.report.LPReport;
import xf.xflp.report.ContainerReport;
import xf.xflp.report.ContainerReportSummary;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@RestController
public class CalculationController {

    @CrossOrigin(origins = "http://localhost:3000")
    @PostMapping("/calculate/xflp")
    public ResponseEntity<?> handleXflpCalculation(@RequestBody CalculationRequest request) {
        try {
            Container container = request.getContainer();
            List<Box> items = request.getItems();
            List<Group> groups = request.getGroups(); // Ambil data grup

            if (container == null || items == null || items.isEmpty()) {
                return ResponseEntity.badRequest().body("Data 'container' dan 'items' tidak boleh kosong.");
            }

            XFLP xflp = new XFLP();
            xflp.setTypeOfOptimization(XFLPOptType.BEST_FIXED_CONTAINER_PACKER);
            xflp.getParameter().setPreferredPackingStrategy(Strategy.TOUCHING_PERIMETER);

            xflp.addContainer()
                .setContainerType("API_Container")
                .setWidth((int) container.getWidth())
                .setLength((int) container.getLength())
                .setHeight((int) container.getHeight())
                .setMaxWeight((float) container.getMaxWeight());

            for (Box apiBox : items) {
                for (int i = 0; i < apiBox.getQuantity(); i++) {
                    xflp.addItem()
                        .setExternID(apiBox.getId() + "-" + (i + 1))
                        .setWidth((int) apiBox.getWidth())
                        .setLength((int) apiBox.getLength())
                        .setHeight((int) apiBox.getHeight())
                        .setWeight((float) apiBox.getWeight())
                        .setSpinnable(true);
                }
            }

            xflp.executeLoadPlanning();
            
            // Teruskan data grup ke adapter
            CalculationResult standardResult = adaptResult(xflp.getReport(), container, items, groups);
            
            return ResponseEntity.ok(standardResult);

        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("Gagal melakukan kalkulasi: " + e.getMessage());
        }
    }

    private CalculationResult adaptResult(LPReport report, Container container, List<Box> originalItems, List<Group> groups) {
        CalculationResult result = new CalculationResult();

        // Membuat map untuk mencari warna berdasarkan nama grup
        Map<String, String> groupColorMap = groups.stream()
                .collect(Collectors.toMap(Group::getName, Group::getColor, (c1, c2) -> c1));

        if (report == null || report.getContainerReports().isEmpty() || report.getContainerReports().get(0).getPackageEvents().isEmpty()) {
            result.setFillRate(0);
            result.setTotalWeight(0);
            result.setPlacedItems(new ArrayList<>());
            result.setUnplacedItems(originalItems);
            result.setContainerVolume(container.getVolume());
            return result;
        }

        Map<String, Box> originalItemsMap = originalItems.stream()
                .collect(Collectors.toMap(Box::getId, Function.identity()));

        List<PlacedBox> placedBoxes = new ArrayList<>();
        Pattern pattern = Pattern.compile("id=(.*?), x=(.*?), y=(.*?), z=(.*?), w=(.*?), l=(.*?), h=(.*?),");

        ContainerReport containerReport = report.getContainerReports().get(0);
        containerReport.getPackageEvents().forEach(p -> {
            Matcher matcher = pattern.matcher(p.toString());
            if (matcher.find()) {
                PlacedBox box = new PlacedBox();
                String fullId = matcher.group(1).trim();
                String originalId = fullId.substring(0, fullId.lastIndexOf('-'));
                Box originalBox = originalItemsMap.get(originalId);

                box.setId(fullId);
                box.setX(Double.parseDouble(matcher.group(2).trim()));
                box.setY(Double.parseDouble(matcher.group(3).trim()));
                box.setZ(Double.parseDouble(matcher.group(4).trim()));
                box.setLength(Double.parseDouble(matcher.group(5).trim()));
                box.setWidth(Double.parseDouble(matcher.group(6).trim()));
                box.setHeight(Double.parseDouble(matcher.group(7).trim()));
                
                if (originalBox != null) {
                    box.setWeight(originalBox.getWeight());
                    // Menetapkan warna berdasarkan grup dari box asli
                    String color = groupColorMap.getOrDefault(originalBox.getGroup(), "#cccccc"); // Default ke abu-abu jika grup tidak ditemukan
                    box.setColor(color);
                }
                
                placedBoxes.add(box);
            }
        });

        ContainerReportSummary summary = containerReport.getSummary();
        result.setPlacedItems(placedBoxes);
        
        if (summary.getMaxVolume() > 0) {
            result.setFillRate((summary.getMaxUsedVolume() / summary.getMaxVolume()) * 100);
        } else {
            result.setFillRate(0);
        }

        result.setContainerVolume(container.getVolume());
        result.setTotalWeight(placedBoxes.stream().mapToDouble(PlacedBox::getWeight).sum());
        result.setUnplacedItems(new ArrayList<>());

        return result;
    }
}

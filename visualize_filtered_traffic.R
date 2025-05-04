#!/usr/bin/env Rscript

# visualize_filtered_traffic.R — финальная визуализация трафика по реальным улицам Алматы

# 1. Настройка
geojson_file <- "almaty_traffic_filtered.geojson"
if (!file.exists(geojson_file)) stop(paste("Файл не найден:", geojson_file))

# 2. Библиотеки
library(sf)
library(dplyr)
library(leaflet)
library(htmlwidgets)

# 3. Загрузка GeoJSON
df <- st_read(geojson_file, quiet = TRUE)

# 4. Подготовка данных
df <- df %>%
  mutate(
    speed_ratio = pmin(speed_kmph / freeFlowSpeed, 1.2),  # ограничим максимум
    name = ifelse(is.na(name), "Без названия", name)
  )

# 5. Цветовая шкала
pal <- colorNumeric(palette = "RdYlGn", domain = c(0.4, 1.2), reverse = FALSE)

# 6. Создание карты
m <- leaflet(df) %>%
  addTiles(group = "OSM") %>%
  addPolylines(
    color = ~pal(speed_ratio),
    weight = 4,
    opacity = 0.9,
    label = ~paste0(name, "<br>Скорость: ", round(speed_kmph), " км/ч"),
    highlightOptions = highlightOptions(color = "blue", weight = 6),
    group = "Пробки"
  ) %>%
  addLegend(
    pal = pal,
    values = ~speed_ratio,
    title = "Загруженность (скорость / свободная)",
    position = "bottomright"
  ) %>%
  addLayersControl(
    baseGroups = c("OSM"),
    overlayGroups = c("Пробки"),
    options = layersControlOptions(collapsed = FALSE)
  )

# 7. Сохранение
dir.create("output", showWarnings = FALSE)
saveWidget(m, file = "output/traffic_filtered_map.html", selfcontained = FALSE)

message("✔ Карта готова: output/traffic_filtered_map.html")

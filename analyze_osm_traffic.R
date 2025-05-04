#!/usr/bin/env Rscript

# analyze_osm_traffic.R — визуализация пробок по реальным улицам OSM

# 1. Настройка
geojson_file <- "osm_almaty_traffic.geojson"
if (!file.exists(geojson_file)) stop(paste("Файл не найден:", geojson_file))

# 2. Библиотеки
library(sf)
library(dplyr)
library(leaflet)
library(htmlwidgets)

# 3. Загрузка GeoJSON
df <- st_read(geojson_file, quiet = TRUE)

# 4. Подготовка: расчёт отношения скорости
df <- df %>%
  mutate(speed_ratio = pmin(speed_kmph / freeFlowSpeed, 1.2))  # ограничим до 1.2 для стабильной легенды

# 5. Палитра и карта
pal <- colorNumeric("RdYlGn", domain = df$speed_ratio, reverse = FALSE)

m <- leaflet(df) %>%
  addTiles(group = "OSM") %>%
  addPolylines(
    color = ~pal(speed_ratio),
    weight = 5,
    opacity = 0.9,
    label = ~paste0(name, ": ", round(speed_kmph), " км/ч"),
    group = "Пробки"
  ) %>%
  addLegend(
    pal = pal,
    values = ~speed_ratio,
    title = "Текущая загруженность<br>(отношение к свободному потоку)",
    position = "bottomright"
  ) %>%
  addLayersControl(
    baseGroups = c("OSM"),
    overlayGroups = c("Пробки"),
    options = layersControlOptions(collapsed = FALSE)
  )

# 6. Сохранение
dir.create("output", showWarnings = FALSE)
saveWidget(m, file = "output/osm_traffic_map.html", selfcontained = FALSE)

message("Готово! Карта сохранена в: output/osm_traffic_map.html")

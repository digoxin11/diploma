#!/usr/bin/env Rscript

# visualize_segmented_traffic.R — визуализация сегментированного трафика с переключателем по времени

# 1. Папка
geojson_dir <- "almaty_traffic_segmented"
if (!dir.exists(geojson_dir)) stop("Папка не найдена: almaty_traffic_segmented")

# 2. Библиотеки
library(sf)
library(dplyr)
library(leaflet)
library(htmlwidgets)
library(glue)
library(stringr)

# 3. Получаем список файлов
geojson_files <- list.files(
  path = geojson_dir,
  pattern = "^almaty_traffic_segmented_\\d{2}\\.geojson$",
  full.names = TRUE
)

if (length(geojson_files) == 0) stop("Нет GeoJSON-файлов")

# 4. Генерация HTML-карт
dir.create("output/maps", recursive = TRUE, showWarnings = FALSE)

for (file in geojson_files) {
  hour_str <- str_extract(basename(file), "\\d{2}")
  df <- st_read(file, quiet = TRUE)

  df <- df %>%
    mutate(
      speed_ratio = pmin(speed_kmph / freeFlowSpeed, 1.2),
      name = ifelse(is.na(name), "Без названия", name)
    )

  pal <- colorNumeric("RdYlGn", domain = c(0.4, 1.2), reverse = FALSE)

  m <- leaflet(df) %>%
    addTiles(group = "OSM") %>%
    addPolylines(
      color = ~pal(speed_ratio),
      weight = 4,
      opacity = 0.9,
      label = ~paste0(name, "<br>", round(speed_kmph), " км/ч"),
      group = "Пробки"
    ) %>%
    addLegend(
      pal = pal,
      values = ~speed_ratio,
      title = paste0("Трафик на ", hour_str, ":00"),
      position = "bottomright"
    )

  saveWidget(m, file = paste0("output/maps/map_", hour_str, ".html"), selfcontained = FALSE)
}

# 5. HTML интерфейс выбора
select_options <- paste0(
  '<option value="maps/map_', str_pad(0:23, 2, pad = "0"), '.html">',
  str_pad(0:23, 2, pad = "0"), ":00",
  '</option>',
  collapse = "\n"
)

index_html <- glue('
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Сегментированный трафик Алматы</title>
  <style>
    body {{ font-family: sans-serif; padding: 1rem; }}
    iframe {{ width: 100%; height: 600px; border: none; }}
  </style>
</head>
<body>
  <h1>Карта пробок по времени</h1>
  <select id="timeSelector">
    {select_options}
  </select>

  <iframe id="mapFrame" src="maps/map_00.html"></iframe>

  <script>
    document.getElementById("timeSelector").addEventListener("change", function () {{
      document.getElementById("mapFrame").src = this.value;
    }});
  </script>
</body>
</html>
')

writeLines(index_html, "output/index.html")

print("✅ Карта готова: output/index.html — переключатель с 24 часами")


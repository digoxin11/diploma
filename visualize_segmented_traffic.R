#!/usr/bin/env Rscript

geojson_dir <- "almaty_traffic_segmented_realistic"

if (!dir.exists(geojson_dir)) stop("Папка не найдена: almaty_traffic_segmented_realistic")

library(sf)
library(dplyr)
library(leaflet)
library(htmlwidgets)
library(glue)
library(stringr)

geojson_files <- list.files(
  path = geojson_dir,
  pattern = "^almaty_traffic_segmented_\\d{2}\\.geojson$",
  full.names = TRUE
)

if (length(geojson_files) == 0) stop("Нет GeoJSON-файлов")

dir.create("output/maps", recursive = TRUE, showWarnings = FALSE)

for (file in geojson_files) {
  hour_str <- str_extract(basename(file), "\\d{2}")
  message(glue("⏳ Обрабатывается час: {hour_str}"))

  df <- st_read(file, quiet = TRUE)

  df <- df %>%
    filter(!is.na(name)) %>%  # отсекаем пустые
    mutate(
      speed_ratio = pmin(speed_kmph / freeFlowSpeed, 1.0)
    )

  pal <- colorNumeric("RdYlGn", domain = c(0.3, 1.0))

  m <- leaflet(df, options = leafletOptions(preferCanvas = TRUE)) %>%
    addTiles(group = "OSM") %>%
    addPolylines(
      color = ~pal(speed_ratio),
      weight = 2,
      opacity = 0.8,
      label = ~paste0(name, "<br>", round(speed_kmph), " км/ч"),
      group = "Пробки"
    ) %>%
    addLegend(
      pal = pal,
      values = ~speed_ratio,
      title = paste0("Трафик в ", hour_str, ":00"),
      position = "bottomright"
    )

  saveWidget(m, file = paste0("output/maps/map", hour_str, ".html"), selfcontained = FALSE)
  message(glue("✅ Сохранён: output/maps/map{hour_str}.html"))
}

select_options <- paste0(
  '<option value="maps/map', str_pad(0:23, 2, pad = "0"), '.html">',
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

  <iframe id="mapFrame" src="maps/map00.html"></iframe>

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
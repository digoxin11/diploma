#!/usr/bin/env Rscript

# analyze_traffic_csv.R — анализ сгенерированного CSV с визуализацией по времени

# 1. Настройка
csv_file <- "generated_traffic_data_almaty.csv"
if (!file.exists(csv_file)) stop(paste("Файл не найден:", csv_file))

# 2. Библиотеки
library(dplyr)
library(tidyr)
library(ggplot2)
library(sf)
library(leaflet)
library(htmlwidgets)
library(lubridate)
library(tibble)
library(glue)
library(purrr)

# 3. Загрузка CSV и генерация геометрии
message("Загружаем данные...")

df_csv <- read.csv(csv_file, stringsAsFactors = FALSE)

set.seed(42)  # постоянные координаты для каждой точки
coords_table <- tibble(
  point = unique(df_csv$point),
  lat = runif(length(unique(df_csv$point)), min = 43.1, max = 43.3),
  lon = runif(length(unique(df_csv$point)), min = 76.8, max = 77.1)
)

df <- df_csv %>%
  mutate(
    timestamp = as.POSIXct(timestamp, tz = "Asia/Almaty"),
    freeFlowSpeed = speed_kmph * runif(n(), 1.1, 1.3),
    currentSpeed = speed_kmph
  ) %>%
  left_join(coords_table, by = "point") %>%
  mutate(
    geometry = map2(lon, lat, ~ st_point(c(.x, .y))),
    geometry = st_sfc(geometry, crs = 4326)
  ) %>%
  distinct(point, timestamp, .keep_all = TRUE) %>%
  mutate(
    frc = "FRC1",
    currentTravelTime = 60 / currentSpeed,
    freeFlowTravelTime = 60 / freeFlowSpeed,
    confidence = 0.95,
    roadClosure = FALSE,
    version = "mock"
  )

df_sf <- st_as_sf(df, sf_column_name = "geometry", crs = 4326)

# 4. Сводная статистика
summary_df <- df %>%
  summarise(
    avg_currentSpeed  = mean(currentSpeed, na.rm = TRUE),
    avg_freeFlowSpeed = mean(freeFlowSpeed, na.rm = TRUE),
    congestion_rate   = mean(currentSpeed < freeFlowSpeed, na.rm = TRUE)
  )
print(summary_df)

# 5. Гистограмма общая
df %>%
  mutate(speed_ratio = currentSpeed / freeFlowSpeed) %>%
  ggplot(aes(speed_ratio)) +
    geom_histogram(binwidth = 0.05, fill = "darkorange", alpha = 0.8) +
    labs(
      title = "Распределение отношения текущей скорости к свободному потоку",
      x = "currentSpeed / freeFlowSpeed",
      y = "Количество точек"
    ) -> p
ggsave("speed_ratio_hist.png", p, width = 6, height = 4)

# 6. Гистограмма почасовая
df_plot <- df %>%
  filter(!is.na(timestamp)) %>%
  mutate(
    speed_ratio = currentSpeed / freeFlowSpeed,
    hour_group = floor_date(timestamp, "hour")
  )

if (nrow(df_plot) > 0) {
  df_plot %>%
    ggplot(aes(x = speed_ratio)) +
      geom_histogram(binwidth = 0.05, fill = "steelblue", alpha = 0.7) +
      facet_wrap(~ hour_group, scales = "free_y") +
      labs(
        title = "Почасовое распределение скоростного отношения",
        x = "currentSpeed / freeFlowSpeed",
        y = "Количество точек"
      ) -> p_time
  ggsave("speed_ratio_by_time.png", p_time, width = 12, height = 8)
}

# 7. Генерация HTML-карт
dir.create("output/maps", recursive = TRUE, showWarnings = FALSE)

df %>%
  filter(!is.na(timestamp)) %>%
  mutate(hour_group = floor_date(timestamp, "hour")) %>%
  group_split(hour_group) %>%
  walk(function(group_df) {
    hour <- unique(group_df$hour_group)
    group_sf <- st_as_sf(group_df, sf_column_name = "geometry", crs = 4326)
    fname <- paste0("output/maps/map_", format(hour, "%Y%m%d_%H"), ".html")

    pal <- colorNumeric("RdYlGn", domain = group_df$currentSpeed / group_df$freeFlowSpeed)
    leaflet(group_sf) %>%
      addTiles() %>%
      addCircleMarkers(
        color = ~pal(currentSpeed / freeFlowSpeed),
        radius = 4,
        stroke = FALSE,
        fillOpacity = 0.8
      ) %>%
      addLegend(
        pal = pal,
        values = ~currentSpeed / freeFlowSpeed,
        title = format(hour, "%Y-%m-%d %H:00"),
        position = "bottomright"
      ) %>%
      htmlwidgets::saveWidget(file = fname, selfcontained = FALSE)
  })

# 8. HTML-переключатель
hours <- df %>%
  filter(!is.na(timestamp)) %>%
  mutate(hour_group = floor_date(timestamp, "hour")) %>%
  distinct(hour_group) %>%
  arrange(hour_group) %>%
  pull(hour_group)

select_options <- paste0(
  '<option value="maps/map_', format(hours, "%Y%m%d_%H"), '.html">',
  format(hours, "%Y-%m-%d %H:00"),
  '</option>',
  collapse = "\n"
)

index_html <- glue('
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Карта пробок по времени</title>
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

  <iframe id="mapFrame" src="maps/map_{format(hours[1], "%Y%m%d_%H")}.html"></iframe>

  <script>
    document.getElementById("timeSelector").addEventListener("change", function () {{
      document.getElementById("mapFrame").src = this.value;
    }});
  </script>
</body>
</html>
')

writeLines(index_html, "output/index.html")

# 9. CSV-экспорт
df %>%
  select(-geometry) %>%
  write.csv("segments_summary.csv", row.names = FALSE)

message("Анализ завершён.
- Таблица: segments_summary.csv
- Гистограммы: speed_ratio_hist.png, speed_ratio_by_time.png
- HTML-карты: output/maps/
- Переключатель по времени: output/index.html")

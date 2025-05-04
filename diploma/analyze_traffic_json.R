#!/usr/bin/env Rscript

# analyze_traffic_json.R
# Скрипт для анализа JSON-файлов Traffic Flow API в R (VS Code, Windows)
# Требуется: jsonlite, dplyr, purrr, tidyr, ggplot2, sf, leaflet (optional), htmlwidgets

# 1. Устанавливаем рабочую директорию (где лежит папка "diploma")
json_dir <- "diploma"  # замените на свой путь, например: "C:/Users/YourName/Documents/GitHub/diploma"
if (!dir.exists(json_dir)) stop(paste("Directory not found:", json_dir))

# 2. Собираем все JSON-файлы рекурсивно
json_files <- list.files(
  path = json_dir,
  pattern = "^traffic_.*\\.json$",
  full.names = TRUE,
  recursive = TRUE
)
if (length(json_files) == 0) stop("Не найдено ни одного JSON-файла в папке: ", json_dir)

# 3. Загружаем библиотеки
library(jsonlite)
library(dplyr)
library(purrr)
library(tidyr)
library(ggplot2)
library(sf)
library(leaflet)
library(htmlwidgets)

# 4. Функция парсинга одного JSON-файла
parse_segment <- function(file) {
  data <- fromJSON(file)
  seg  <- data$flowSegmentData
  coords <- seg$coordinates$coordinate %>% 
    tibble::as_tibble() %>% 
    select(lon = longitude, lat = latitude)

  tibble(
    file       = basename(file),
    frc        = seg$frc,
    currentSpeed       = seg$currentSpeed,
    freeFlowSpeed      = seg$freeFlowSpeed,
    currentTravelTime  = seg$currentTravelTime,
    freeFlowTravelTime = seg$freeFlowTravelTime,
    confidence = seg$confidence,
    roadClosure= seg$roadClosure,
    version    = data$`@version`,
    geometry   = list(st_linestring(as.matrix(coords)))
  )
}

# 5. Парсим все файлы
df <- map_dfr(json_files, parse_segment)

# 6. Преобразуем в sf-объект для гео-визуализации
df_sf <- st_as_sf(df, sf_column_name = "geometry", crs = 4326)

# 7. Сводная статистика по скорости и заторам
summary_df <- df %>%
  summarise(
    avg_currentSpeed  = mean(currentSpeed, na.rm = TRUE),
    avg_freeFlowSpeed = mean(freeFlowSpeed, na.rm = TRUE),
    congestion_rate   = mean(currentSpeed < freeFlowSpeed, na.rm = TRUE)
  )
print(summary_df)

# 8. Строим гистограмму отношения скоростей
df %>%
  mutate(speed_ratio = currentSpeed / freeFlowSpeed) %>%
  ggplot(aes(speed_ratio)) +
    geom_histogram(binwidth = 0.05) +
    labs(
      title = "Распределение отношения текущей скорости к свободному потоку",
      x = "currentSpeed / freeFlowSpeed",
      y = "Количество сегментов"
    ) -> p
ggsave(filename = "speed_ratio_hist.png", plot = p, width = 6, height = 4)

# 9. Интерактивная карта (Leaflet)
pal <- colorNumeric("RdYlGn", domain = df$currentSpeed / df$freeFlowSpeed)
leaflet(df_sf) %>%
  addTiles() %>%
  addPolylines(
    color = ~pal(currentSpeed / freeFlowSpeed),
    weight = 3, opacity = 0.8
  ) %>%
  addLegend(
    pal = pal,
    values = ~currentSpeed / freeFlowSpeed,
    title = "Speed Ratio",
    position = "bottomright"
  ) -> m
# Сохраняем карту в HTML (без selfcontained, чтобы не требовать Pandoc)
htmlwidgets::saveWidget(m, "traffic_map.html", selfcontained = FALSE)

# 10. Экспорт итоговой таблицы (без geometry)
df %>%
  select(-geometry) %>%
  write.csv("segments_summary.csv", row.names = FALSE)

message("Анализ завершён.\n- Сводная таблица: segments_summary.csv\n- Гистограмма: speed_ratio_hist.png\n- Карта: traffic_map.html")

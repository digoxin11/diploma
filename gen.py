import os

# Название каталога проекта
project_dir = "almaty_traffic_project"

# Создаём структуру проекта: корневой каталог и подкаталог src
os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)

# 1. Создание файла src/main.c
main_c = r'''\
#include <SDL.h>
// Предполагается, что заголовочные файлы Dear ImGui и его реализации доступны
#include "imgui.h"
#include "imgui_impl_sdl.h"
#include "imgui_impl_sdlrenderer.h"
#include <stdio.h>
#include <stdbool.h>

int main(int argc, char* argv[])
{
    // Инициализация SDL
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER | SDL_INIT_EVENTS) != 0)
    {
        printf("Error: %s\n", SDL_GetError());
        return -1;
    }
    
    // Создание окна
    SDL_Window *window = SDL_CreateWindow("Almaty Traffic Dashboard",
                                            SDL_WINDOWPOS_CENTERED,
                                            SDL_WINDOWPOS_CENTERED,
                                            1280, 720,
                                            SDL_WINDOW_SHOWN);
    if (!window)
    {
        printf("Ошибка создания окна: %s\n", SDL_GetError());
        SDL_Quit();
        return -1;
    }
    
    // Создание рендерера
    SDL_Renderer *renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    if (!renderer)
    {
        printf("Ошибка создания рендерера: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return -1;
    }

    // Настройка Dear ImGui
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO &io = ImGui::GetIO(); (void)io;
    // Можно настроить стили (например, эффект dark)
    ImGui::StyleColorsDark();

    // Инициализация backend-ов SDL2 и SDL_Renderer для ImGui
    ImGui_ImplSDL2_InitForSDLRenderer(window, renderer);
    ImGui_ImplSDLRenderer_Init(renderer);

    bool done = false;
    while (!done)
    {
        // Обработка событий SDL
        SDL_Event event;
        while (SDL_PollEvent(&event))
        {
            ImGui_ImplSDL2_ProcessEvent(&event);
            if (event.type == SDL_QUIT)
                done = true;
            if (event.type == SDL_WINDOWEVENT &&
                event.window.event == SDL_WINDOWEVENT_CLOSE &&
                event.window.windowID == SDL_GetWindowID(window))
                done = true;
        }
        
        // Начало нового кадра ImGui
        ImGui_ImplSDLRenderer_NewFrame();
        ImGui_ImplSDL2_NewFrame(window);
        ImGui::NewFrame();

        // Пример интерфейса: окно с заголовком, текстом и кнопкой
        {
            ImGui::Begin("Almaty Traffic Dashboard");
            ImGui::Text("Это демо окно на базе SDL2 и Dear ImGui");
            if (ImGui::Button("Exit"))
                done = true;
            ImGui::End();
        }
        
        // Рендеринг ImGui
        ImGui::Render();
        SDL_SetRenderDrawColor(renderer, 30, 30, 30, 255); // фон
        SDL_RenderClear(renderer);
        ImGui_ImplSDLRenderer_RenderDrawData(ImGui::GetDrawData());
        SDL_RenderPresent(renderer);
    }
    
    // Очистка
    ImGui_ImplSDLRenderer_Shutdown();
    ImGui_ImplSDL2_Shutdown();
    ImGui::DestroyContext();
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
'''

main_c_path = os.path.join(project_dir, "src", "main.c")
with open(main_c_path, "w", encoding="utf-8") as f:
    f.write(main_c)

# 2. Создание файла Makefile
makefile_content = r'''\
CC = gcc
CFLAGS = -O2 -Wall -std=c11 `sdl2-config --cflags` -I./include
LIBS = `sdl2-config --libs` -lSDL2 -lSDL2_ttf -lSDL2_image -lSDL2_mixer -lm

# Предполагаем, что библиотека Dear ImGui (или cimgui) установлена и доступна для линковки
# Для простоты добавляем ключ -limgui
SRCS = src/main.c
OBJS = $(SRCS:.c=.o)
TARGET = almaty_traffic

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS) $(LIBS) -limgui

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)
'''

makefile_path = os.path.join(project_dir, "Makefile")
with open(makefile_path, "w", encoding="utf-8") as f:
    f.write(makefile_content)

# 3. Создание файла README.md
readme_content = r'''\
# Almaty Traffic Project

Этот проект демонстрирует базовое приложение на Си с использованием SDL2 и Dear ImGui.
Программа открывает окно с интерфейсом "Almaty Traffic Dashboard" с кнопкой "Exit".

## Требования

- SDL2 (разработческие библиотеки)
- Dear ImGui (или cimgui, C-обёртка для Dear ImGui)
- Компилятор GCC (или аналогичный)
- sdl2-config (для автоматического получения флагов компиляции)

## Сборка

В терминале (в каталоге проекта) выполните команду:

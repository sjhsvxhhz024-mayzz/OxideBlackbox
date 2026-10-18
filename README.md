# TEZEROK

Игра на **Godot 4.7**. Этап 1 — главное меню с живой фотореалистичной 3D-сценой; модели сделаны с помощью ИИ и **Blender 5.2**.

![Главное меню](docs/main_menu.jpg)

## Запуск
1. Установите [Godot 4.7](https://godotengine.org/download) (Standard, не .NET).
2. Откройте `project.godot` и нажмите **F5**. При первом открытии Godot импортирует модели — это займёт около минуты.

## Что есть в меню
- **Фотореалистичная сцена по концепту**: фон и персонаж восстановлены из концепт-арта ИИ-моделями (см. ниже) и стоят в 3D — камера слегка дрейфует и даёт параллакс за мышью.
- **Персонаж**: рельефная 3D-модель с ригом из 20 костей и зацикленной idle-анимацией на 8 секунд — дыхание, лёгкое покачивание, поворот головы, покачивание шлема в руке; модуль на бедре пульсирует голубым.
- **Живой фон**: облака плывут, из труб идёт дым, по долине ползёт дымка, трава и деревья качаются на ветру, море рябит, по земле и персонажу проходят тени облаков, мигает маяк на вышке, мерцают огни завода, летают птицы, в воздухе висят пылинки.
- **Кнопки**: «ИГРАТЬ», «ПЕРСОНАЖ» и «НАСТРОЙКИ» пока показывают подсказку «скоро» (это следующие этапы), «ВЫХОД» закрывает игру. Работают мышь, клавиатура (стрелки + Enter) и геймпад.

## Как сделаны модели (ИИ + Blender)
Всё работает локально на CPU, без регистраций и ключей:

| Шаг | Скрипт | ИИ-модель (лицензия) |
| --- | --- | --- |
| Глубина сцены и маска персонажа | `tools/ai_pipeline/analyze_reference.py` | Depth Anything V2 Small (Apache-2.0), rembg IS-Net (Apache-2.0) |
| Фон без персонажа и интерфейса | `tools/ai_pipeline/clean_plate.py` | LaMa (Apache-2.0) |
| Глубина в метрах, маски анимации, текстура персонажа | `tools/ai_pipeline/build_layers.py` | — |
| 3D-модель фона и риг персонажа с анимацией | `blender/build_menu_scene.py` | Blender 5.2 |

```bash
uv venv .tools/aienv --python 3.12
uv pip install --python .tools/aienv/bin/python torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .tools/aienv/bin/python transformers "rembg[cpu]" onnxruntime opencv-python-headless huggingface_hub
.tools/aienv/bin/python tools/ai_pipeline/analyze_reference.py tools/ai_pipeline/work/reference.png
.tools/aienv/bin/python tools/ai_pipeline/clean_plate.py
.tools/aienv/bin/python tools/ai_pipeline/build_layers.py
blender -b --factory-startup --python blender/build_menu_scene.py
blender -b --factory-startup --python blender/build_props.py   # птица и текстура дыма
```

Модели пишутся в `assets/models/*.glb` (их использует Godot) и `blender/menu_scene.blend` (для правки в Blender).
Полноценную 360° модель персонажа для геймплея можно сгенерировать в TRELLIS.2 (Hugging Face, MIT), когда у бесплатной квоты есть время.

## Структура
| Путь | Что внутри |
| --- | --- |
| `scenes/main_menu.tscn` | Главное меню: панель, кнопки, интро, подсказки |
| `scenes/menu_world.tscn` | 3D-сцена меню: камера, фон, персонаж |
| `scripts/` | Логика меню, эффектов (дым, дымка, птицы, маяк, огни, пыль) и камеры |
| `shaders/` | «Живая фотография» фона, персонаж, свечения, птицы, размытие панели |
| `tools/ai_pipeline/` | ИИ-обработка концепта (глубина, маски, дорисовка фона) |
| `blender/` | Сборка 3D-моделей и файлы `.blend` |
| `assets/` | Модели `.glb`, текстуры сцены, текстура дыма, шрифт Oswald (лицензия OFL) |

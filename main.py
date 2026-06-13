import os
import sys

from compiler.generator import GeoDraftGenerator
from compiler.parser import GeoDraftParser
from compiler.translator import GeoDraftTranslator


def compile_geodraft(json_path: str, output_path: str = None):
    if not os.path.exists(json_path):
        print(f"Ошибка: Файл '{json_path}' не найден.")
        return False

    if not output_path:
        base, _ = os.path.splitext(json_path)
        output_path = base + ".ggb"

    parser = GeoDraftParser()
    translator = GeoDraftTranslator()
    generator = GeoDraftGenerator()

    # main.py (фрагмент в методе compile_geodraft)
    try:
        print(f"-> Чтение и валидация '{json_path}'...")
        doc = parser.parse_file(json_path)

        # Запускаем Rejection Sampling под ограничения
        print("-> Подбор параметров конфигурации под ограничения (constraints)...")
        from compiler.sampler import sample_and_evaluate

        sampled_state = sample_and_evaluate(doc)

        print("-> Трансляция математической логики и конфигураций View...")
        project = translator.translate_project(doc, sampled_state)

        # Собираем типы для корректного маппинга XML-элементов
        original_types = {obj.name: obj.type for obj in doc.construction if obj.name}

        print("-> Генерация XML и сборка ZIP-пакета .ggb...")
        generator.create_ggb(project, original_types, output_path)

        print(f" Успешно скомпилировано! Файл сохранен: {output_path}")
        return True
    except Exception as e:
        print(f" Ошибка компиляции: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python main.py <путь_к_json_файлу> [выходной_файл.ggb]")
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    success = compile_geodraft(json_path, output_path)
    sys.exit(0 if success else 1)

import argparse
import glob
import os
import sys
import traceback

try:
    from compiler.config import GeoDrawConfig
    from compiler.core.sampler import sample_and_evaluate
    from compiler.core.translator import GeoDraftTranslator
    from compiler.generator import GeoDraftGenerator
    from compiler.parser import GeoDraftParser

except ImportError as e:
    print(
        "[-] Ошибка импорта! Убедитесь, что запускаете main.py из правильной директории."
    )
    print(f"    Детали ошибки: {e}")
    sys.exit(1)


def compile_geodraft(
    json_path: str,
    output_path: str | None = None,
    quiet: bool = False,
    config_path: str | None = None,
) -> tuple[bool, str]:
    """
    Компилирует один файл GeoDraft JSON в .ggb.
    Возвращает (успех: bool, сообщение_об_ошибке/детали: str)
    """
    if not os.path.exists(json_path):
        return False, f"Файл '{json_path}' не найден."

    if not output_path:
        base, _ = os.path.splitext(json_path)
        output_path = base + ".ggb"

    config = (
        GeoDrawConfig.load_from_file(config_path) if config_path else GeoDrawConfig()
    )
    parser = GeoDraftParser()
    translator = GeoDraftTranslator()
    generator = GeoDraftGenerator(config=config)

    try:
        if not quiet:
            print(f"-> Чтение и валидация '{json_path}'...")
        doc = parser.parse_file(json_path)

        if not quiet:
            print("-> Подбор параметров конфигурации под ограничения (constraints)...")
        sampled_state = sample_and_evaluate(doc)
        if not sampled_state:
            return (
                False,
                "Не удалось подобрать конфигурацию под constraints (Rejection Sampling исчерпан).",
            )

        if not quiet:
            print("-> Трансляция математической логики и конфигураций View...")
        project = translator.translate_project(doc, sampled_state)

        original_types = {}
        for obj in doc.construction:
            if obj.name:
                original_types[obj.name] = obj.type
            elif obj.names:
                for n in obj.names:
                    original_types[n] = obj.type

        if not quiet:
            print("-> Генерация XML и сборка ZIP-пакета .ggb...")
        generator.create_ggb(project, original_types, output_path)

        return True, f"Успешно сохранен: {output_path}"

    except Exception as e:
        err_msg = str(e)
        if not quiet:
            traceback.print_exc()
        return False, err_msg


def run_batch_tests(tests_dir: str):
    """
    Автоматический тест-раннер. Находит все .json файлы в папке,
    компилирует их в тихом режиме и выводит сводный красивый отчет.
    """
    if not os.path.isdir(tests_dir):
        print(f"[-] Ошибка: Директория с тестами '{tests_dir}' не найдена.")
        return

    search_path = os.path.join(tests_dir, "**", "*.json")
    json_files = glob.glob(search_path, recursive=True)

    if not json_files:
        print(
            f"[-] В директории '{tests_dir}' не найдено файлов .json для тестирования."
        )
        return

    print(f"\n=== Запуск тестирования GeoDraw ({len(json_files)} тестов) ===")

    success_count = 0
    failed_tests = []

    for idx, filepath in enumerate(json_files, 1):
        rel_path = os.path.relpath(filepath, tests_dir)
        print(
            f"[{idx}/{len(json_files)}] Тестируем {rel_path:40} ... ",
            end="",
            flush=True,
        )

        success, message = compile_geodraft(filepath, quiet=True)

        if success:
            print("\033[92m[OK]\033[0m")
            success_count += 1
        else:
            print("\033[91m[FAIL]\033[0m")
            failed_tests.append((rel_path, message))

    print("\n================ Результаты тестирования ================")
    print(f" Успешно пройдено: {success_count} / {len(json_files)}")

    if failed_tests:
        print(f" Провалено тестов: {len(failed_tests)}")
        print("\nДетали ошибок:")
        for name, err in failed_tests:
            print(f"  - \033[91m{name}\033[0m: {err}")
    else:
        print(" Все тесты успешно пройдены!")
    print("=========================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GeoDraw Compiler")
    parser.add_argument(
        "input_json", help="Путь к JSON файлу задачи или папке с тестами", nargs="?"
    )
    parser.add_argument("output_ggb", help="Выходной файл .ggb", nargs="?")
    parser.add_argument(
        "--test", action="store_true", help="Запустить режим тестирования"
    )
    parser.add_argument(
        "--style", "-s", type=str, help="Путь к JSON файлу с кастомным стилем"
    )

    args = parser.parse_args()

    if args.test:
        if not args.input_json:
            print("Ошибка: Укажите папку с тестами.")
            sys.exit(1)
        run_batch_tests(args.input_json)
    else:
        if not args.input_json:
            parser.print_help()
            sys.exit(1)

        success, msg = compile_geodraft(
            args.input_json, args.output_ggb, config_path=args.style
        )
        if success:
            print(f"\033[92m[+] SUCCESS:\033[0m {msg}")
            sys.exit(0)
        else:
            print(f"\033[91m[-] ERROR:\033[0m {msg}")
            sys.exit(1)

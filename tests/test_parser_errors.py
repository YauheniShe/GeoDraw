import os
import tempfile

import pytest

# Предполагается, что парсер находится в compiler.parser (или compiler.core.parser)
from compiler.parser import GeoDraftParser


def test_parser_json_syntax_error():
    """Тест 1: Забытая запятая в JSON (JSONDecodeError)"""
    parser = GeoDraftParser()

    # Намеренно делаем ошибку в JSON: забыта запятая после "problem_name": "Test"
    bad_json_content = """
    {
        "problem_name": "Test"
        "constraints": []
    }
    """

    # Создаем временный файл
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp:
        tmp.write(bad_json_content)
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError) as exc_info:
            parser.parse_file(tmp_path)

        error_msg = str(exc_info.value)

        # Проверяем, что сработал наш красивый перехватчик JSONDecodeError
        assert "[!] Ошибка синтаксиса JSON в файле" in error_msg
        assert "Проверьте запятые и кавычки." in error_msg
    finally:
        os.remove(tmp_path)


def test_parser_missing_required_field():
    """Тест 2: Забыто обязательное поле (ValidationError: Field required)"""
    parser = GeoDraftParser()

    # Передаем валидный JSON-словарь, но без обязательного поля "problem_name"
    bad_data = {"constraints": [], "construction": [], "goals": [], "view": []}

    with pytest.raises(ValueError) as exc_info:
        parser.parse_dict(bad_data)

    error_msg = str(exc_info.value)

    assert "[!] Ошибка валидации структуры документа GeoDraft:" in error_msg
    assert "❌ Поле: problem_name" in error_msg
    assert "Отсутствует обязательное поле" in error_msg


def test_parser_invalid_literal():
    """Тест 3: Неверное название метода (ValidationError: Input should be...)"""
    parser = GeoDraftParser()

    bad_data = {
        "problem_name": "Invalid Literal Test",
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "MagicMethod",  # Такого метода нет, должен быть Free/Intersection и т.д.
                "args": None,
            }
        ],
    }

    with pytest.raises(ValueError) as exc_info:
        parser.parse_dict(bad_data)

    error_msg = str(exc_info.value)

    assert "[!] Ошибка валидации структуры документа GeoDraft:" in error_msg
    assert "❌ Поле: construction[0]" in error_msg
    # Pydantic предложит варианты, мы проверяем замену текста
    assert "Ожидалось значение:" in error_msg


def test_parser_extra_forbidden_field():
    """Тест 4: Передача лишнего аргумента, который запрещен (Extra inputs not permitted)"""
    parser = GeoDraftParser()

    # Для метода Intersection разрешены только obj1 и obj2. Передадим obj3.
    bad_data = {
        "problem_name": "Extra Field Test",
        "construction": [
            {
                "name": "P",
                "type": "Point",
                "method": "Intersection",
                "args": {
                    "obj1": "Line1",
                    "obj2": "Line2",
                    "obj3": "Line3",
                },
            }
        ],
    }

    with pytest.raises(ValueError) as exc_info:
        parser.parse_dict(bad_data)

    error_msg = str(exc_info.value)

    assert "[!] Ошибка валидации структуры документа GeoDraft:" in error_msg
    assert "❌ Поле: construction[0].args.obj3" in error_msg
    assert "Передано лишнее/неизвестное поле" in error_msg


def test_parser_nested_validation_error():
    """Тест 5: Ошибка глубоко внутри массива (например в constraints)"""
    parser = GeoDraftParser()

    bad_data = {
        "problem_name": "Deep Error Test",
        "constraints": [
            {
                "type": "IsAcute",
                "args": {
                    "points": [
                        "A",
                        "B",
                    ]
                },
            },
            {
                "type": "NonCollinear",
                "args": {},
            },
        ],
    }

    with pytest.raises(ValueError) as exc_info:
        parser.parse_dict(bad_data)

    error_msg = str(exc_info.value)
    assert "❌ Поле: constraints[1].args.points" in error_msg
    assert "Отсутствует обязательное поле" in error_msg

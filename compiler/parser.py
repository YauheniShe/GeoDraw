import json
import re

from pydantic import ValidationError

from compiler.models import GeoDraftDocument


class GeoDraftParser:
    def __init__(self):
        self.anon_counter = 1

    def parse_file(self, filepath: str) -> GeoDraftDocument:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"\n[!] Ошибка синтаксиса JSON в файле '{filepath}':\n"
                f"    Строка {e.lineno}, колонка {e.colno}: {e.msg}\n"
                f"    Проверьте запятые и кавычки."
            )
        except FileNotFoundError:
            raise ValueError(f"\n[!] Файл не найден: {filepath}")

        return self.parse_dict(data)

    def parse_dict(self, data: dict) -> GeoDraftDocument:
        flat_construction_data = self._flatten_construction(
            data.get("construction", [])
        )

        data["construction"] = flat_construction_data

        try:
            return GeoDraftDocument(**data)
        except ValidationError as e:
            error_msgs = ["\n[!] Ошибка валидации структуры документа GeoDraft:"]
            grouped_errors = {}

            for err in e.errors():
                base_path, model_name, sub_path = self._analyze_loc(err["loc"])
                msg = err["msg"]

                if base_path not in grouped_errors:
                    grouped_errors[base_path] = {}
                if model_name not in grouped_errors[base_path]:
                    grouped_errors[base_path][model_name] = []
                grouped_errors[base_path][model_name].append((sub_path, msg))

            for base_path, models in grouped_errors.items():
                best_models = []
                for m_name, errs in models.items():
                    type_failed = any(
                        (
                            len(sp) > 0
                            and sp[0] in ("type", "method")
                            and ("Input should be" in m or "value" in m)
                        )
                        for sp, m in errs
                    )
                    if not type_failed:
                        best_models.append(m_name)

                kept_errors = []
                if best_models:
                    for m_name in best_models:
                        kept_errors.extend(models[m_name])
                else:
                    for m_name, errs in models.items():
                        kept_errors.extend(errs)

                seen = set()
                for sub_path, msg in kept_errors:
                    if msg.startswith("Input should be"):
                        msg = msg.replace("Input should be", "Ожидалось значение:")
                    elif msg == "Field required":
                        msg = "Отсутствует обязательное поле"
                    elif "Extra inputs are not permitted" in msg:
                        msg = "Передано лишнее/неизвестное поле"

                    path_str = self._format_path(base_path, sub_path)
                    if not path_str:
                        path_str = "Корень документа"

                    dup_key = (path_str, msg)
                    if dup_key not in seen:
                        seen.add(dup_key)
                        error_msgs.append(
                            f"  ❌ Поле: {path_str}\n     Проблема: {msg}"
                        )

            raise ValueError("\n".join(error_msgs))

    def _analyze_loc(self, loc: tuple):
        """
        Разбивает кортеж loc на:
        1. base_path — путь до элемента в массиве (например: ('construction', 0))
        2. model_name — имя класса Pydantic (например: 'ObjPointIntersection')
        3. sub_path — путь внутри модели (например: ('args', 'obj3'))
        """
        base_path = []
        model_name = None
        sub_path = []

        for item in loc:
            if model_name is not None:
                sub_path.append(item)
            elif isinstance(item, int):
                base_path.append(item)
            elif isinstance(item, str):
                m = re.search(r"\b(Obj[A-Za-z]+|Constraint[A-Za-z]+)\b", item)
                if m:
                    model_name = m.group(1)
                elif "function-" in item or "check_" in item:
                    m_inner = re.search(r"\b(Obj[A-Za-z]+|Constraint[A-Za-z]+)\b", item)
                    if m_inner:
                        model_name = m_inner.group(1)
                else:
                    base_path.append(item)
        return tuple(base_path), model_name, tuple(sub_path)

    def _format_path(self, base_path: tuple, sub_path: tuple) -> str:
        clean_sub = [item for item in sub_path if item not in ("[key]", "[value]")]
        full_path = list(base_path) + clean_sub

        path_parts = []
        for loc in full_path:
            if isinstance(loc, int):
                path_parts.append(f"[{loc}]")
            else:
                path_parts.append(f".{loc}")
        return "".join(path_parts).lstrip(".")

    def _flatten_construction(self, construction_list: list) -> list:
        flat_list = []
        system_keys = {"name", "names", "type", "method", "hidden", "disambiguation"}

        def process_node(node):
            if isinstance(node, list):
                return [process_node(item) for item in node]
            elif isinstance(node, dict):
                processed_dict = {k: process_node(v) for k, v in node.items()}

                if (
                    "type" in processed_dict
                    and "name" not in processed_dict
                    and "names" not in processed_dict
                ):
                    anon_name = f"anon{self.anon_counter}"
                    self.anon_counter += 1

                    extracted_obj = processed_dict.copy()

                    if "args" not in extracted_obj:
                        args_payload = {
                            k: v
                            for k, v in extracted_obj.items()
                            if k not in system_keys
                        }
                        extracted_obj = {
                            k: v for k, v in extracted_obj.items() if k in system_keys
                        }
                        extracted_obj["args"] = args_payload if args_payload else None

                    extracted_obj["name"] = anon_name
                    extracted_obj["hidden"] = True

                    flat_list.append(extracted_obj)
                    return anon_name

                return processed_dict
            else:
                return node

        for top_obj in construction_list:
            processed_obj = top_obj.copy()

            if processed_obj.get("args"):
                processed_obj["args"] = process_node(processed_obj["args"])
            else:
                args_payload = {
                    k: v for k, v in processed_obj.items() if k not in system_keys
                }
                if args_payload:
                    processed_obj["args"] = process_node(args_payload)
                for k in args_payload.keys():
                    processed_obj.pop(k, None)

            if processed_obj.get("disambiguation"):
                processed_obj["disambiguation"] = process_node(
                    processed_obj["disambiguation"]
                )

            flat_list.append(processed_obj)

        return flat_list

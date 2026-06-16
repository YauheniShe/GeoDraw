import json

from compiler.models import GeoDraftDocument


class GeoDraftParser:
    def __init__(self):
        self.anon_counter = 1

    def parse_file(self, filepath: str) -> GeoDraftDocument:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.parse_dict(data)

    def parse_dict(self, data: dict) -> GeoDraftDocument:
        flat_construction_data = self._flatten_construction(
            data.get("construction", [])
        )

        data["construction"] = flat_construction_data

        return GeoDraftDocument(**data)

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

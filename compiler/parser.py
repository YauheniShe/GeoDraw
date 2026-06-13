import json

from .models import GeoDraftDocument, GeoObject


class GeoDraftParser:
    def __init__(self):
        self.anon_counter = 1

    def parse_file(self, filepath: str) -> GeoDraftDocument:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.parse_dict(data)

    def parse_dict(self, data: dict) -> GeoDraftDocument:
        required_keys = {"problem_name", "constraints", "construction", "goals", "view"}
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            raise ValueError(f"Missing keys: {missing_keys}")

        flat_construction_data = self._flatten_construction(data["construction"])

        system_keys = {"name", "names", "type", "method", "hidden", "disambiguation"}

        construction_objects = []
        for obj_data in flat_construction_data:
            if "args" in obj_data:
                args_payload = obj_data["args"]
            else:
                args_payload = {
                    k: v for k, v in obj_data.items() if k not in system_keys
                }
                if not args_payload:
                    args_payload = None

            construction_objects.append(
                GeoObject(
                    name=obj_data.get("name"),
                    names=obj_data.get("names"),
                    type=obj_data.get("type"),
                    method=obj_data.get("method"),
                    args=args_payload,
                    hidden=obj_data.get("hidden", False),
                    disambiguation=obj_data.get("disambiguation"),
                )
            )

        return GeoDraftDocument(
            problem_name=data["problem_name"],
            constraints=data["constraints"],
            construction=construction_objects,
            goals=data["goals"],
            view=data["view"],
        )

    def _flatten_construction(self, construction_list: list) -> list:
        flat_list = []

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
            if processed_obj.get("disambiguation"):
                processed_obj["disambiguation"] = process_node(
                    processed_obj["disambiguation"]
                )

            flat_list.append(processed_obj)

        return flat_list

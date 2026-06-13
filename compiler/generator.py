import xml.etree.ElementTree as ET
import zipfile
from typing import Dict

from .translator import CompiledProject


class GeoDraftGenerator:
    def __init__(self):
        pass

    def generate_xml(
        self, project: CompiledProject, original_types: Dict[str, str]
    ) -> str:
        root = ET.Element("geogebra", format="5.0", version="5.0.357.0")

        gui = ET.SubElement(root, "gui")
        ET.SubElement(gui, "window", width="800", height="600")

        view = ET.SubElement(root, "euclidianView")
        ET.SubElement(view, "size", width="800", height="600")
        ET.SubElement(view, "coordSystem", xZero="250", yZero="350", scale="50")

        ET.SubElement(view, "axis", id="0", show="false")
        ET.SubElement(view, "axis", id="1", show="false")
        ET.SubElement(view, "grid", show="false")

        construction = ET.SubElement(root, "construction", title="GeoDraft Export")

        for instr in project.instructions:
            ET.SubElement(
                construction, "expression", label=instr.name, exp=instr.expression
            )

            el_type = instr.ggb_type

            elem = ET.SubElement(
                construction, "element", type=el_type, label=instr.name
            )

            if instr.coords and el_type == "point":
                ET.SubElement(
                    elem,
                    "coords",
                    x=str(instr.coords[0]),
                    y=str(instr.coords[1]),
                    z="1.0",
                )

            show_val = "true" if project.visibility.get(instr.name, True) else "false"

            show_label = (
                "true"
                if el_type == "point" and not instr.name.startswith("anon")
                else "false"
            )
            ET.SubElement(elem, "show", object=show_val, label=show_label)

            is_goal = getattr(instr, "is_goal", False)

            if is_goal:
                alpha_val = "0.1" if el_type == "angle" else "0.0"
                ET.SubElement(elem, "objColor", r="200", g="0", b="0", alpha=alpha_val)
            else:
                alpha_val = "0.0" if el_type in ["polygon", "conic", "angle"] else "1.0"
                ET.SubElement(elem, "objColor", r="0", g="0", b="0", alpha=alpha_val)

            if el_type in ["line", "segment", "ray", "conic", "polygon", "angle"]:
                l_type = "15" if is_goal else "0"
                thickness = "3" if is_goal else "2"
                ET.SubElement(elem, "lineStyle", thickness=thickness, type=l_type)
            elif el_type == "point":
                p_size = "4" if is_goal else "3"
                p_style = "4" if is_goal else "0"
                ET.SubElement(elem, "pointSize", val=p_size)
                ET.SubElement(elem, "pointStyle", val=p_style)

            if el_type == "angle":
                ET.SubElement(elem, "angleStyle", val="1")

        xml_str = ET.tostring(root, encoding="utf-8").decode("utf-8")
        return '<?xml version="1.0" encoding="utf-8"?>\n' + xml_str

    def create_ggb(
        self, project: CompiledProject, original_types: Dict[str, str], output_path: str
    ):
        xml_content = self.generate_xml(project, original_types)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("geogebra.xml", xml_content)
            zip_file.writestr("geogebra_javascript.js", "function ggbOnInit() {}")

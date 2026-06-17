import xml.etree.ElementTree as ET
import zipfile
from typing import Dict

from compiler.config import GeoDrawConfig
from compiler.core.translator import CompiledProject


class GeoDraftGenerator:
    def __init__(self, config: GeoDrawConfig | None = None):
        self.config = config or GeoDrawConfig()

    def generate_xml(
        self, project: CompiledProject, original_types: Dict[str, str]
    ) -> str:
        root = ET.Element("geogebra", format="5.0", version="5.0.357.0")

        gui = ET.SubElement(root, "gui")
        ET.SubElement(gui, "window", width="800", height="600")

        view = ET.SubElement(root, "euclidianView")
        ET.SubElement(view, "size", width="800", height="600")
        ET.SubElement(view, "coordSystem", xZero="250", yZero="350", scale="50")

        show_ax_str = str(self.config.show_axes).lower()
        show_gr_str = str(self.config.show_grid).lower()
        ET.SubElement(view, "axis", id="0", show=show_ax_str)
        ET.SubElement(view, "axis", id="1", show=show_ax_str)
        ET.SubElement(view, "grid", show=show_gr_str)

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

            is_goal = getattr(instr, "is_goal", False)
            if is_goal:
                style = self.config.goal
            elif el_type == "point":
                style = self.config.point
            elif el_type == "polygon":
                style = self.config.polygon
            elif el_type == "angle":
                style = self.config.angle
            else:
                style = self.config.line

            show_val = "true" if project.visibility.get(instr.name, True) else "false"

            is_helper = (
                instr.name.startswith("anon")
                or instr.name.startswith("draw")
                or instr.name.startswith("goal")
            )

            if not is_helper and style.label_style != "none":
                show_label = "true"
            else:
                show_label = "false"

            ET.SubElement(elem, "show", object=show_val, label=show_label)

            if show_label == "true":
                if style.label_style == "latex":
                    ET.SubElement(elem, "labelMode", val="3")
                    ET.SubElement(elem, "caption", val=f"${instr.name}$")
                elif style.label_style == "name":
                    ET.SubElement(elem, "labelMode", val="0")

            r, g, b = style.color
            if el_type in ["angle", "polygon"]:
                alpha_val = str(style.alpha)
            else:
                alpha_val = "0.0"

            ET.SubElement(
                elem, "objColor", r=str(r), g=str(g), b=str(b), alpha=alpha_val
            )

            if el_type in ["line", "segment", "ray", "conic", "polygon", "angle"]:
                ET.SubElement(
                    elem,
                    "lineStyle",
                    thickness=str(style.line_thickness),
                    type=str(style.line_style),
                )

            if el_type == "point":
                ET.SubElement(elem, "pointSize", val=str(style.point_size))
                ET.SubElement(elem, "pointStyle", val=str(style.point_style))

            if el_type == "angle":
                ET.SubElement(elem, "allowReflexAngle", val="false")
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

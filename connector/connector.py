#!/usr/bin/env python3
import inkex
from lxml import etree as ET
import math

class ConnectorExtension(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--stroke_width", type=float, default=1.0, help="Width of the stroke in mm")
        pars.add_argument("--text_size", type=float, default=10.0, help="Size of the text in px")
        pars.add_argument("--scale_factor", type=float, default=1.0, help="Factor to scale the measurement")
        pars.add_argument("--text_raise", type=float, default=5.0, help="Distance to raise text from the path")

    def effect(self):
        if len(self.svg.selection) < 2:
            inkex.errormsg("Please select at least two objects.")
            return
        self.create_or_find_defs()
        sorted_objects = sorted(self.svg.selection.items(), key=lambda x: x[1].get('id'))
        for i in range(len(sorted_objects) - 1):
            start_obj = sorted_objects[i][1]
            end_obj = sorted_objects[i + 1][1]
            start_center = self.get_center(start_obj)
            end_center = self.get_center(end_obj)
            self.create_line_and_text(start_center, end_center)

    def create_or_find_defs(self):
        svg_root = self.document.getroot()
        nsmap = {"svg": "http://www.w3.org/2000/svg"}
        defs = svg_root.find('.//svg:defs', namespaces=nsmap)
        if defs is None:
            defs = ET.SubElement(svg_root, '{{{}}}defs'.format(nsmap["svg"]))
        self.create_arrowhead_marker(defs, nsmap)

    def create_arrowhead_marker(self, defs, nsmap):
        self.marker_base_length = 10
        marker = ET.SubElement(defs, '{{{}}}marker'.format(nsmap["svg"]), {
            'id': 'Arrowhead',
            'viewBox': '0 0 10 10',
            'refX': '5',
            'refY': '5',
            'markerUnits': 'strokeWidth',
            'markerWidth': '4',
            'markerHeight': '3',
            'orient': 'auto-start-reverse',
        })
        ET.SubElement(marker, '{{{}}}path'.format(nsmap["svg"]), {
            'd': 'M 0 0 L 10 5 L 0 10 z',
            'fill': 'black'
        })

    def get_center(self, element):
        # Check for nesting and apply transformations if needed
        transformation = self.calculate_nested_transformation(element)
        bbox = element.bounding_box(transformation)
        return ((bbox.left + bbox.right) / 2, (bbox.top + bbox.bottom) / 2)

    def calculate_nested_transformation(self, element):
        # Calculate the transformation if the element is nested
        transformation = inkex.Transform()
        while element.getparent() is not None:
            if isinstance(element.getparent(), inkex.Group):
                transformation = element.getparent().transform @ transformation
            element = element.getparent()
        return transformation

    def calculate_offset(self, start, end, stroke_width):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx ** 2 + dy ** 2)
        if length == 0:
            return start, end
        actual_marker_length = self.marker_base_length * stroke_width / 2
        offset_length = actual_marker_length / length
        offset_x = dx * offset_length
        offset_y = dy * offset_length
        return (start[0] + offset_x, start[1] + offset_y), (end[0] - offset_x, end[1] - offset_y)

    def create_line_and_text(self, start, end):
        stroke_width_mm = self.options.stroke_width
        adjusted_start, adjusted_end = self.calculate_offset(start, end, stroke_width_mm)
        line_attribs = {
            'd': f'M {adjusted_start[0]},{adjusted_start[1]} L {adjusted_end[0]},{adjusted_end[1]}',
            'style': f'stroke:black;stroke-width:{stroke_width_mm}mm;fill:none;marker-start:url(#Arrowhead);marker-end:url(#Arrowhead)'
        }
        line = inkex.PathElement(attrib=line_attribs)
        self.svg.get_current_layer().append(line)
        bbox = self.calculate_bounding_box(start, end)
        length = self.get_longest_side_length(bbox) / 1000  # Convert to meters
        scaled_length = length * self.options.scale_factor  # Apply scale factor
        self.create_text_label(start, end, scaled_length, bbox, stroke_width_mm)

    def calculate_bounding_box(self, start, end):
        left = min(start[0], end[0])
        right = max(start[0], end[0])
        top = min(start[1], end[1])
        bottom = max(start[1], end[1])
        return (left, top, right, bottom)

    def get_longest_side_length(self, bbox):
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return max(width, height)

    def create_text_label(self, start, end, scaled_length, bbox, stroke_width):
        path_midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        angle = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))
        text_size = self.options.text_size
        text = inkex.TextElement()
        text.text = f"{scaled_length:.2f} m"
        text_style = f'font-size:{text_size}px; text-anchor:middle'
        text.set('style', text_style)
        self.align_textbox(text, path_midpoint, angle, bbox, stroke_width)
        self.svg.get_current_layer().append(text)

    def align_textbox(self, text_element, midpoint, angle, path_bbox, stroke_width):
        offset = self.options.text_raise
        rad_angle = math.radians(angle)

        # Determine if the path is pointing leftward and adjust the angle
        is_leftward = (angle > 90 and angle <= 180) or (angle < -90 and angle >= -180)
        if is_leftward:
            rad_angle += math.pi
            angle += 180

        # Calculate offset direction (perpendicular to path)
        offset_x = offset * math.cos(rad_angle - math.pi / 2)
        offset_y = offset * math.sin(rad_angle - math.pi / 2)

        # Apply offset based on path orientation
        final_x = midpoint[0] + offset_x
        final_y = midpoint[1] + offset_y

        text_element.set('x', str(final_x))
        text_element.set('y', str(final_y))
        text_element.set('transform', f'rotate({angle},{final_x},{final_y})')

if __name__ == '__main__':
    ConnectorExtension().run()

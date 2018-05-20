import logging
import os
from itertools import groupby
from typing import Dict, Tuple, List, Union

import svgwrite.animate
import svgwrite.container
import svgwrite.path
import svgwrite.shapes
import svgwrite.text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class AsciiChar:
    def __init__(self, value=None, text_color='foreground', background_color='background'):
        # type: (AsciiChar, Union[str, None], Union[str, None], Union[str, None]) -> None
        if value is not None and len(value) > 1:
            raise ValueError(f'Invalid value: {value}')

        self.value = value
        self.text_color = text_color
        self.background_color = background_color

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f'{self.value} ({self.text_color}, {self.background_color})'

    def __eq__(self, other):
        # type: (AsciiChar, AsciiChar) -> bool
        if isinstance(other, self.__class__):
            return all(self.__getattribute__(attr) == other.__getattribute__(attr)
                       for attr in ('value', 'text_color', 'background_color'))
        else:
            return False

    def __hash__(self):
        return hash(repr(self))


class AsciiAnimation:
    def __init__(self, lines=24, columns=80):
        self.lines = lines
        self.columns = columns
        self.defs = {}

    def _render_line_bg_colors(self, screen_line, height, line_height):
        # type: (AsciiAnimation, Dict[int, AsciiChar], float, float) -> List[svgwrite.shapes.Rect]
        def make_rectangle(group: List[int]) -> svgwrite.shapes.Rect:
            x = f'{group[0]}ex'
            y = f'{height:.2f}em'
            sx = f'{len(group)}ex'
            sy = f'{line_height:.2f}em'
            args = {
                'insert': (x, y),
                'size': (sx, sy),
                'class': screen_line[group[0]].background_color
            }
            return svgwrite.shapes.Rect(**args)

        group = []
        groups = []
        cols = {col for col in screen_line if screen_line[col].background_color is not None}
        for index in sorted(cols):
            group.append(index)
            if index + 1 not in screen_line or \
                    screen_line[index].background_color != screen_line[index + 1].background_color:
                if screen_line[index].background_color != 'background':
                    groups.append(group)
                group = []

        rectangles = [make_rectangle(group) for group in groups]
        return rectangles

    # TODO: Merge rectangles over multiple lines
    # def _render_frame_bg_colors(self, screen_buffer, line_height):
    #     # type: (AsciiAnimation, Dict[int, Dict[int, AsciiChar]], float, str) -> List[svgwrite.shapes.Rect]
    #     rects = []
    #     for row in screen_buffer:
    #         height = row * line_height + 0.25
    #         rects += self._render_line_bg_colors(screen_buffer[row], height, line_height)
    #     return rects

    def _render_characters(self, screen_line, height):
        # type: (AsciiAnimation, Dict[int, AsciiChar], float) -> Tuple[Union[svgwrite.text.Text, None], svgwrite.text.Use]
        """Render a screen of the terminal as a list of SVG text elements

        Characters with the same attributes (color) are grouped together in a
        single text element.

        :param screen_line: Mapping between positions on the row and characters
        :param height: Vertical position of the line
        :return: List of SVG text elements
        """
        def group_key(item):
            _, char = item
            return char.text_color

        def sort_key(item):
            col, char = item
            return char.text_color, col

        chars = {(col, char) for (col, char) in screen_line.items() if char.value is not None}
        sorted_chars = sorted(chars, key=sort_key)

        text = svgwrite.text.Text(text='')
        for attributes, group in groupby(sorted_chars, key=group_key):
            color = attributes
            tspan_attributes = {}
            classes = []
            if color != 'foreground':
                classes.append(color)

            if classes:
                tspan_attributes['class'] = ' '.join(classes)

            group_chars = [(index, (char.value if char.value != ' ' else u'\u00A0'))
                           for index, char in group]

            content = ''.join(c for _, c in group_chars)
            xs = [f'{col}ex' for col, _ in group_chars]
            tspan = svgwrite.text.TSpan(text=content, x=xs, **tspan_attributes)
            text.add(tspan)

        text_str = text.tostring()
        if text_str not in self.defs:
            self.defs[text_str] = len(self.defs) + 1
            text.attribs['id'] = self.defs[text_str]
        else:
            text = None

        use = svgwrite.container.Use(href=f'#{self.defs[text_str]}', y=f'{height:.2f}em')
        return text, use

    # def _render_frame_fg(self, screen_buffer, line_height, group_id):
    #     # type: (AsciiAnimation, Dict[int, Dict[int, AsciiChar]], float, str) -> svgwrite.container.Group
    #     frame = svgwrite.container.Group(id=group_id)
    #     for row in screen_buffer:
    #         svg_items = self._render_characters(screen_buffer[row], height=(row + 1) * line_height)
    #         for item in svg_items:
    #             frame.add(item)
    #     return frame
    #
    # def _render_frame(self):
    #     pass

    def render_animation(self, records, filename, color_conf, end_pause=1):
        if end_pause < 0:
            raise ValueError(f'Invalid end_pause (must be >= 0): "{end_pause}"')

        font_size = 14
        css = {
            # Apply this style to each and every element since we are using coordinates that
            # depend on the size of the font
            '*': {
                'font-family': '"DejaVu Sans Mono", monospace',
                'font-style': 'normal',
                'font-size': f'{font_size}px',
            },
            'text': {
                'fill': color_conf['foreground']
            },
            '.bold': {
                'font-weight': 'bold'
            }
        }
        css_ansi_colors = {f'.{color}': {'fill': color_conf[color]} for color in color_conf}
        css.update(css_ansi_colors)

        # Line_height in 'em' unit
        line_height = 1.10
        width = self.columns
        height = (self.lines + 1) * line_height

        dwg = svgwrite.Drawing(filename, (f'{width}ex', f'{height}em'), debug=True)
        dwg.defs.add(dwg.style(AsciiAnimation._serialize_css_dict(css)))
        args = {
            'insert': (0, 0),
            'size': ('100%', '100%'),
            'class': 'background'
        }
        r = svgwrite.shapes.Rect(**args)
        dwg.add(r)

        def by_time(record):
            row, line, current_time, line_duration = record
            return current_time, line_duration

        for animation_id, (group_key, line_group) in enumerate(groupby(records, key=by_time)):
            group = svgwrite.container.Group(display='none')

            for row, line, _, _ in line_group:
                height = row * line_height + 0.25
                svg_items = self._render_line_bg_colors(line, height, line_height)
                for item in svg_items:
                    group.add(item)

                height = (row + 1) * line_height
                line_def, line_use = self._render_characters(line, height)
                if line_def is not None:
                    dwg.defs.add(line_def)
                group.add(line_use)

            current_time, line_duration = group_key
            extra = {
                'id': animation_id,
                'begin': f'{current_time:.3f}s',
                'dur': f'{line_duration:.3f}s',
                'values': 'inline;inline',
                'keyTimes': '0.0;1.0',
                'fill': 'remove'
            }
            group.add(svgwrite.animate.Animate('display', **extra))
            dwg.add(group)

        dwg.save()

    @staticmethod
    def _serialize_css_dict(css):
        # type: (Dict[str, Dict[str, str]]) -> str
        def serialize_css_item(item):
            return '; '.join(f'{prop}: {item[prop]}' for prop in item)

        items = [f'{item} {{{serialize_css_item(css[item])}}}' for item in css]
        return os.linesep.join(items)

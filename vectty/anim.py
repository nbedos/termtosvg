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

    @classmethod
    def from_pyte(cls, char):
        """Create an AsciiChar from a pyte character"""
        colors = {
            'black': 'color0',
            'red': 'color1',
            'green': 'color2',
            'brown': 'color3',
            'blue': 'color4',
            'magenta': 'color5',
            'cyan': 'color6',
            'white': 'color7',
        }

        colors_bold = {
            'black': 'color8',
            'red': 'color9',
            'green': 'color10',
            'brown': 'color11',
            'blue': 'color12',
            'magenta': 'color13',
            'cyan': 'color14',
            'white': 'color15',
        }

        if char.fg == 'default':
            text_color = 'foreground'
        elif char.fg in colors:
            if char.bold:
                text_color = colors_bold[char.fg]
            else:
                text_color = colors[char.fg]
        else:
            text_color = char.fg

        if char.bg == 'default':
            background_color = 'background'
        elif char.bg in colors:
            background_color = colors[char.bg]
        else:
            background_color = char.bg

        if char.reverse:
            text_color, background_color = background_color, text_color

        return AsciiChar(char.data, text_color, background_color)


class AsciiAnimation:
    def __init__(self, lines=24, columns=80):
        self.lines = lines
        self.columns = columns
        self.defs = {}

    def _render_line_bg_colors(self, screen_line, height, line_height):
        # type: (AsciiAnimation, Dict[int, AsciiChar], float, float) -> List[svgwrite.shapes.Rect]
        def make_rectangle(group: List[int]) -> svgwrite.shapes.Rect:
            x = f'{group[0] * 8}'
            y = f'{height}'
            sx = f'{len(group) * 8}'
            sy = f'{line_height}'
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
        # type: (AsciiAnimation, Dict[int, AsciiChar], float) -> List[svgwrite.text.Tspan]
        """Render a screen of the terminal as a list of SVG text elements

        Characters with the same attributes (color) are grouped together in a
        single text element.

        :param screen_line: Mapping between positions on the row and characters
        :param height: Vertical position of the line
        :return: List of SVG text elements
        """

        def make_text(group: List[int]) -> svgwrite.text.Text:
            text = ''.join(screen_line[c].value for c in group)
            attributes = {
                'text': text.replace(' ', u'\u00A0'),
                'x': [str(group[0] * 8)],
                'textLength': f'{len(group) * 8}',
                'lengthAdjust': 'spacingAndGlyphs',
            }
            if screen_line[group[0]].text_color != 'foreground':
                attributes['class'] = screen_line[group[0]].text_color

            return svgwrite.text.Text(**attributes)

        group = []
        groups = []
        cols = {col for col in screen_line if screen_line[col].background_color is not None}
        for col in sorted(cols):
            group.append(col)
            if col + 1 not in screen_line or \
                    screen_line[col].text_color != screen_line[col+1].text_color:
                groups.append(group)
                group = []

        texts = [make_text(group) for group in groups]
        return texts

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
                'fill': color_conf['foreground'],
                'dominant-baseline': 'text-before-edge'
            },
            '.bold': {
                'font-weight': 'bold'
            }
        }
        css_ansi_colors = {f'.{color}': {'fill': color_conf[color]} for color in color_conf}
        css.update(css_ansi_colors)

        cell_width = 8
        cell_height = 17
        width = self.columns * cell_width
        height = self.lines * cell_height

        dwg = svgwrite.Drawing(filename, (f'{width}', f'{height}'), debug=True)
        dwg.defs.add(dwg.style(AsciiAnimation._serialize_css_dict(css)))
        args = {
            'insert': (0, 0),
            'size': ('100%', '100%'),
            'class': 'background'
        }
        r = svgwrite.shapes.Rect(**args)
        dwg.add(r)

        def by_time(record):
            _, _, line_time, line_duration = record
            return line_time, line_duration

        row_animations = {}
        last_animation_id_str = 'anim_last'
        animation = None
        for animation_id, (key, line_group) in enumerate(groupby(records, key=by_time)):
            line_time, line_duration = key
            frame = svgwrite.container.Group(display='none')

            animation_begin = None
            animation_id_str = f'anim_{animation_id}'
            for row, line, _, _ in line_group:
                height = row * cell_height
                rects = self._render_line_bg_colors(line, height, cell_height)
                for rect in rects:
                    frame.add(rect)

                g = svgwrite.container.Group()
                for text in self._render_characters(line, height):
                    g.add(text)

                # Define this line or reuse the existing definition
                g_str = g.tostring()
                if g_str in self.defs:
                    group_id = self.defs[g_str]
                else:
                    group_id = len(self.defs) + 1
                    assert group_id not in self.defs
                    self.defs[g_str] = group_id
                    g.attribs['id'] = group_id
                    dwg.defs.add(g)

                frame.add(svgwrite.container.Use(f'#{group_id}', y=height))

                if animation_begin is None and row in row_animations:
                    row_anim_id, row_anim_end = row_animations[row]
                    offset = line_time - row_anim_end
                    animation_begin = f'{row_anim_id}.end+{offset}ms'

                row_animations[row] = (animation_id_str, line_time + line_duration)

            if animation_begin is None:
                animation_begin = f'{line_time}ms;{last_animation_id_str}.end+{line_time}ms'

            extra = {
                'begin': animation_begin,
                'dur': f'{line_duration}ms',
                'from': 'inline',
                'to': 'inline',
                'fill': 'remove',
                'id': animation_id_str
            }

            animation = svgwrite.animate.Animate('display', **extra)
            frame.add(animation)

            dwg.add(frame)

        animation.attribs['id'] = last_animation_id_str
        dwg.save()

    @staticmethod
    def _serialize_css_dict(css):
        # type: (Dict[str, Dict[str, str]]) -> str
        def serialize_css_item(item):
            return '; '.join(f'{prop}: {item[prop]}' for prop in item)

        items = [f'{item} {{{serialize_css_item(css[item])}}}' for item in css]
        return os.linesep.join(items)

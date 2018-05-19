import datetime
from itertools import groupby
import logging
import os
import svgwrite.animate
import svgwrite.container
import svgwrite.path
import svgwrite.shapes
import svgwrite.text
from typing import Dict, Tuple, Generator, List, Iterable, Any, Union


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
    def __init__(self):
        pass

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
        # type: (AsciiAnimation, Dict[int, AsciiChar], float) -> List[svgwrite.text.Text]
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

        svg_items = []
        chars = {(col, char) for (col, char) in screen_line.items() if char.value is not None}
        sorted_chars = sorted(chars, key=sort_key)
        for attributes, group in groupby(sorted_chars, key=group_key):
            color = attributes
            text_attributes = {}
            classes = []
            if color != 'foreground':
                classes.append(color)

            if classes:
                text_attributes['class'] = ' '.join(classes)

            group_chars = [(index, (char.value if char.value != ' ' else u'\u00A0'))
                           for index, char in group]

            text = ''.join(c for _, c in group_chars)
            xs = [f'{col}ex' for col, _ in group_chars]
            ys = [f'{height:.2f}em']
            text = svgwrite.text.Text(text=text, x=xs, y=ys, **text_attributes)

            svg_items.append(text)

        return svg_items

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

    def _buffer_difference(self, last_buffer, next_buffer):
        # type: (AsciiAnimation, Dict[int, Dict[int, Any]], Dict[int, Dict[int, Any]]) -> Dict[int, Dict[int, AsciiChar]]
        diff_buffer = {}
        for row in set(last_buffer) | set(next_buffer):
            if row in next_buffer:
                if row not in last_buffer or last_buffer[row] != next_buffer[row]:
                    diff_buffer[row] = next_buffer[row]
            else:
                # Paint empty cells with the default background color on removed lines
                empty_char = AsciiChar()
                diff_buffer[row] = {col: empty_char for col in last_buffer[row]}

        return diff_buffer

    def _line_timings(self, timings):
        # type: (AsciiAnimation, Iterable[Tuple[Dict[int, Dict[int, AsciiChar]], datetime.timedelta]]) -> Generator[int, Tuple[int, Dict[int, AsciiChar], Union[datetime.timedelta, None], datetime.timedelta], None, None]
        last_buffer = None
        pending_lines = {}
        current_time = datetime.timedelta(seconds=0)
        for screen_buffer, duration in timings:
            if last_buffer is None:
                diff_buffer = screen_buffer
            else:
                diff_buffer = self._buffer_difference(last_buffer, screen_buffer)
            last_buffer = screen_buffer

            for row in pending_lines:
                line, line_time, line_duration = pending_lines[row]
                if row in diff_buffer:
                    yield row, line, line_time, line_duration
                else:
                    pending_lines[row] = line, line_time, line_duration + duration

            for row in diff_buffer:
                pending_lines[row] = diff_buffer[row], current_time, duration

            current_time += duration

        for row in pending_lines:
            line, line_time, line_duration = pending_lines[row]
            yield row, line, line_time, line_duration

    def render_animation(self, timings, filename, color_conf, end_pause=1):
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

        dwg = svgwrite.Drawing(filename, ('80ex', '28em'), debug=True)
        dwg.defs.add(dwg.style(AsciiAnimation._serialize_css_dict(css)))
        args = {
            'insert': (0, 0),
            'size': ('100%', '100%'),
            'class': 'background'
        }
        r = svgwrite.shapes.Rect(**args)
        dwg.add(r)

        # Line_height in 'em' unit
        line_height = 1.10

        row_animations = {}
        for row, line, current_time, line_duration in timings:
            group = svgwrite.container.Group(display='none')

            height = row * line_height + 0.25
            svg_items = self._render_line_bg_colors(line, height, line_height)
            for item in svg_items:
                group.add(item)

            height = (row + 1) * line_height
            svg_items = self._render_characters(line, height)
            for item in svg_items:
                group.add(item)

            if row in row_animations:
                begin = f'animation_{row}_{row_animations[row]}.end'
                animation_id = f'animation_{row}_{row_animations[row]+1}'
                row_animations[row] += 1
            else:
                begin = f'{current_time.total_seconds():.3f}s'
                animation_id = f'animation_{row}_0'
                row_animations[row] = 0

            extra = {
                'id': animation_id,
                'begin': begin,
                'dur': f'{line_duration.total_seconds():.3f}s',
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

from collections import defaultdict
import datetime
import logging
import os
import pty
import pyte
import pyte.screens
import svgwrite.animate
import svgwrite.container
import svgwrite.path
import svgwrite.shapes
import svgwrite.text
import time
from typing import Union, Dict, Set, FrozenSet, Tuple, Any, Callable
from Xlib import display, rdb, Xatom


BUFFER_SIZE = 1024

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# TODO: Group rectangles vertically
# TODO: Use a viewBox to display completed lines (~history)


def cell_neighbours(cell: Tuple[int, int]) -> Set[Tuple[int, int]]:
    i, j = cell
    return {(i-1, j), (i+1, j), (i, j-1), (i, j+1)}


def link_cells(matrix: Dict[int, Dict[int, Any]], key: Callable=lambda x: x) \
        -> Dict[Any, Set[FrozenSet]]:
    """Group the cells of a matrix by value"""
    values = defaultdict(set)
    visited = set()
    for row in matrix:
        for column in matrix[row]:
            if (row, column) in visited:
                continue

            visited_neighbours = set()
            neighbours = cell_neighbours((row, column))
            linked_cells = set()
            while neighbours:
                i, j = neighbours.pop()
                visited_neighbours.add((i, j))
                if i in matrix and j in matrix[i]:
                    if key(matrix[i][j]) == key(matrix[row][column]):
                        linked_cells.add((i, j))
                        neighbours |= (cell_neighbours((i, j)) - visited_neighbours)
            visited |= linked_cells

            values[key(matrix[row][column])].add(frozenset(linked_cells))

    return values


def get_Xresources_colors() -> Dict[str,str]:
    d = display.Display()
    xresources_str = d.screen(0).root.get_full_property(Xatom.RESOURCE_MANAGER,
                                                        Xatom.STRING)
    if xresources_str:
        data = xresources_str.value.decode('utf-8')
    else:
        data = None
    res_db = rdb.ResourceDB(string=data)

    mapping = {
        'foreground': res_db['x.foreground', 'X.Foreground'],
        'background': res_db['x.background', 'X.Background'],
        'black': res_db['x.color0', 'X.Color0'],
        'red': res_db['x.color1', 'X.Color1'],
        'green': res_db['x.color2', 'X.Color2'],
        'brown': res_db['x.color3', 'X.Color3'],
        'blue': res_db['x.color4', 'X.Color4'],
        'magenta': res_db['x.color5', 'X.Color5'],
        'cyan': res_db['x.color6', 'X.Color6'],
        'white': res_db['x.color7', 'X.Color7']
    }
    return mapping


def ansi_color_to_xml(color: str, color_conf: Union[Dict[str, str], None]=None) -> Union[str, None]:
    if color_conf is not None and color in color_conf:
        return color_conf[color]

    # Named colors are also defined in the SVG specification so we can keep them as is
    svg_named_colors = {'black', 'red', 'green', 'brown', 'blue', 'magenta', 'cyan', 'white'}
    if color in svg_named_colors:
        return color

    # Non named colors are passed to this function as a six digit hexadecimal number
    if len(color) == 6:
        # The following instruction will raise a ValueError exception if 'color' is not a
        # valid hexadecimal string
        int(color, 16)
        return f'#{color}'

    raise ValueError(f'Invalid color: "{color}"')


# TODO: Animation pausing
def record():
    shell = os.environ.get('SHELL', 'sh')
    timings = []

    def read(fd):
        data = os.read(fd, BUFFER_SIZE)
        timings.append((data, datetime.datetime.now()))
        return data

    header = f'Script started on {time.asctime()}'
    print(header)

    pty.spawn(shell, read)

    footer = f'Script done on {time.asctime()}'
    print(footer)
    # print(b''.join(d for d, _ in timings))
    return timings


def group_by_time(timings, threshold=datetime.timedelta(milliseconds=50)):
    grouped_timings = []
    current_string = []
    current_time = None
    for character, t in timings:
        if current_time is not None:
            assert t - current_time >= datetime.timedelta(seconds=0)
            if t - current_time > threshold:
                # Flush current string
                s = b''.join(current_string)
                grouped_timings.append((s, current_time))
                current_string = []
                current_time = t
        else:
            current_time = t

        current_string.append(character)

    if current_string:
        grouped_timings.append((b''.join(current_string), current_time))

    return grouped_timings


def serialize_css_dict(css: Dict[str, Dict[str, str]]) -> str:
    def serialize_css_item(item: Dict[str, str]) -> str:
        return '; '.join(f'{prop}: {item[prop]}' for prop in item)

    items = [f'{item} {{{serialize_css_item(css[item])}}}' for item in css]
    return os.linesep.join(items)


def render_animation(timings, filename, end_pause=1):
    if end_pause < 0:
        raise ValueError(f'Invalid end_pause (must be >= 0): "{end_pause}"')
    font_size = 14
    color_conf = get_Xresources_colors()
    css = {
        # Apply this style to each and every element since we are using coordinates that depend on
        # the size of the font
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
    dwg.defs.add(dwg.style(serialize_css_dict(css)))
    args = {
        'insert': (0, 0),
        'size': ('100%', '100%'),
        'class': 'background'
    }
    r = svgwrite.shapes.Rect(**args)
    dwg.add(r)
    input_data, times = zip(*timings)

    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)
    first_animation_begin = f'0s; animation_{len(input_data)-1}.end'
    # Lien_height in 'em' unit
    line_height = 1.10
    for index, bs in enumerate(input_data):
        stream.feed(bs)
        frame = svgwrite.container.Group(id=f'frame_{index}', display='none')

        # Background
        frame_bg = draw_bg(screen.buffer, line_height, f'frame_bg_{index}')
        frame.add(frame_bg)

        # Foreground
        frame_fg = draw_fg(screen.buffer, line_height, f'frame_fg_{index}')
        frame.add(frame_fg)

        # Animation
        try:
            frame_duration = (times[index+1] - times[index]).total_seconds()
        except IndexError:
            frame_duration = end_pause

        assert frame_duration > 0
        extra = {
            'id': f'animation_{index}',
            'begin': f'animation_{index-1}.end' if index > 0 else first_animation_begin,
            'dur': f'{frame_duration:.3f}s',
            'values': 'inline;inline',
            'keyTimes': '0.0;1.0',
            'fill': 'remove'
        }
        frame.add(svgwrite.animate.Animate('display', **extra))
        dwg.add(frame)

    dwg.save()


# TODO: Merge rectangles over multiple lines as in:
# https://stackoverflow.com/questions/5919298/algorithm-for-finding-the-fewest-rectangles-to-cover-a-set-of-rectangles-without/6634668
def draw_bg(screen_buffer, line_height, group_id):
    frame = svgwrite.container.Group(id=group_id)
    for row in screen_buffer.keys():
        last_bg_color = None
        start_col = 0
        last_col = None
        for col in sorted(screen_buffer[row]):
            char = screen_buffer[row][col]
            bg_color = char.fg if char.reverse else char.bg
            if bg_color == 'default':
                if char.reverse:
                    bg_color = 'foreground'
                else:
                    bg_color = 'background'

            if bg_color != last_bg_color or (last_col is not None and col != last_col + 1):
                if last_bg_color is not None and last_bg_color != 'background':
                    args = {
                        'insert': (f'{start_col}ex', f'{row * line_height + 0.25:.2f}em'),
                        'size': (f'{col-start_col}ex', f'{line_height}em'),
                        'class': last_bg_color
                    }
                    r = svgwrite.shapes.Rect(**args)
                    frame.add(r)
                start_col = col
            last_bg_color = bg_color
            last_col = col
        if screen_buffer[row] and last_bg_color is not None and last_bg_color != 'background':
            col = max(screen_buffer[row]) + 1
            args = {
                'insert': (f'{start_col}ex', f'{row * line_height + 0.25:.2f}em'),
                'size': (f'{col-start_col}ex', f'{line_height}em'),
                'class': last_bg_color
            }
            r = svgwrite.shapes.Rect(**args)
            frame.add(r)

    return frame


def draw_fg(screen_buffer, line_height, group_id):
    frame = svgwrite.container.Group(id=group_id)
    for row in screen_buffer:
        height = (row + 1) * line_height
        content = ''
        last_text_attributes = {}
        current_text_position = 0
        last_col = -1

        for col in sorted(screen_buffer[row]):
            char = screen_buffer[row][col]
            # Replace spaces with non breaking spaces so that consecutive spaces
            # are preserved
            data = char.data if char.data != ' ' else u'\u00A0'
            text_attributes = {}

            fg_color = char.bg if char.reverse else char.fg
            if fg_color == 'default' and char.reverse:
                fg_color = 'background'
            classes = []
            if fg_color != 'default':
                classes.append(fg_color)
            if char.bold:
                classes.append('bold')
            if classes:
                text_attributes['class'] = ' '.join(classes)

            if text_attributes != last_text_attributes or col != last_col + 1:
                if content:
                    text = svgwrite.text.Text(text=content,
                                              x=[f'{current_text_position + i}ex' for i in
                                                 range(len(content))],
                                              y=[f'{height:.2f}em'],
                                              **last_text_attributes)
                    frame.add(text)
                content = ''
                current_text_position = col

            content += data
            last_text_attributes = text_attributes
            last_col = col

        if content:
            text = svgwrite.text.Text(text=content,
                                      x=[f'{current_text_position + i}ex' for i in
                                         range(len(content))],
                                      y=[f'{height:.2f}em'],
                                      **last_text_attributes)
            frame.add(text)
    return frame


if __name__ == '__main__':
    timings = record()
    squashed_timings = group_by_time(timings, threshold=datetime.timedelta(milliseconds=40))
    render_animation(squashed_timings, '/tmp/test.svg')

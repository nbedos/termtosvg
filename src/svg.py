import datetime
import logging
import os
import pty
import pyte
import pyte.screens
import svgwrite
import svgwrite.animate
import svgwrite.container
import svgwrite.path
import svgwrite.shapes
import svgwrite.text
import time
from typing import Union


BUFFER_SIZE = 1024

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def ansi_color_to_xml(color: str) -> Union[str, None]:
    if color == "default":
        return None

    # Named colors are also defined in the SVG specification
    svg_named_colors = {'black', 'red', 'green', 'brown', 'blue', 'magenta', 'cyan', 'white'}
    if color in svg_named_colors:
        return color

    # Non named colors are passed to us as a six digit hexadecimal number
    if len(color) == 6:
        # The following instruction will raise a ValueError exception if 'color' is not a
        # valid hexadecimal string
        int(color, 16)
        return f'#{color}'.upper()

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


def render_animation(timings, filename, end_pause=1):
    if end_pause < 0:
        raise ValueError('Invalid end_pause (must be >= 0): "{end_pause}"')

    font = 'Dejavu Sans Mono'
    font_size = 14
    style = f'font-family: {font}; font-style: normal; font-size: {font_size}px;'
    dwg = svgwrite.Drawing(filename, (900, 900), debug=True, style=style)
    input_data, times = zip(*timings)

    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)
    first_animation_begin = f'0s; animation_{len(input_data)-1}.end'
    line_height = font_size + 2
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

# TODO: Merge adjacent cells with the same background color into a polygon
def draw_bg(screen_buffer, line_height, group_id):
    frame = svgwrite.container.Group(id=group_id)
    for row in screen_buffer.keys():
        for col in screen_buffer[row]:
            char = screen_buffer[row][col]
            xml_color = ansi_color_to_xml(char.fg if char.reverse else char.bg)
            if xml_color is None:
                continue

            r = svgwrite.shapes.Rect(insert=(f'{col}ex', 3 + row * line_height),
                                     size=("1ex", line_height),
                                     fill=xml_color)
            frame.add(r)
    return frame


def draw_fg(screen_buffer, line_height, group_id, line_size=80):
    frame = svgwrite.container.Group(id=group_id)
    for row in screen_buffer.keys():
        height = 1 + (row + 1) * line_height
        content = ''
        last_text_attributes = {}
        current_text_position = 0
        last_col = -1

        for col in sorted(screen_buffer[row].keys()):
            char = screen_buffer[row][col]
            # Replace spaces with non breaking spaces so that they are not ignored by browsers
            data = char.data if char.data != ' ' else u'\u00A0'
            text_attributes = {}

            xml_color = ansi_color_to_xml(char.bg if char.reverse else char.fg)
            if xml_color is not None:
                text_attributes['fill'] = xml_color

            if char.bold:
                text_attributes['style'] = 'font-weight:bold;'

            if text_attributes != last_text_attributes or col != last_col + 1:
                if content:
                    text = svgwrite.text.Text(text=content,
                                              textLength=f'{len(content)}ex',
                                              x=[f'{current_text_position}ex'],
                                              y=[height],
                                              **last_text_attributes)
                    frame.add(text)
                content = ''
                current_text_position = col
            content += data
            last_text_attributes = text_attributes

        if content:
            text = svgwrite.text.Text(text=content,
                                      textLength=f'{len(content)}ex',
                                      x=[f'{current_text_position}ex'],
                                      y=[height],
                                      **last_text_attributes)
            frame.add(text)
    return frame


if __name__ == '__main__':
    timings = record()
    squashed_timings = group_by_time(timings, threshold=datetime.timedelta(milliseconds=40))
    render_animation(squashed_timings, '/tmp/test.svg')

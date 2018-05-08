import os
import pty
import svgwrite
import svgwrite.text
import svgwrite.path
import svgwrite.animate
import svgwrite.container
import time
import datetime
import pyte
import pyte.screens
import logging

BUFFER_SIZE = 1024

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        raise ValueError('End pause duration must be greater than or equal to 0 seconds')

    font = 'Dejavu Sans Mono'
    font_size = 14
    style = f'font-family: {font}; font-style: normal; font-size: {font_size}px; white-space: pre;'
    dwg = svgwrite.Drawing(filename, (900, 900), debug=True, style=style)
    input_data, times = zip(*timings)

    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)
    first_animation_begin = f'0s; animation_{len(input_data)-1}.end'
    for index, bs in enumerate(input_data):
        stream.feed(bs)

        frame = draw_screen(screen.buffer, font_size, f'frame_{index}')

        try:
            frame_duration = (times[index+1] - times[index]).total_seconds()
        except IndexError:
            frame_duration = end_pause

        assert frame_duration > 0
        extra = {
            'id': f'animation_{index}',
            'begin': f'animation_{index-1}.end' if index > 0 else first_animation_begin,
            'dur': f'{frame_duration:.3f}s',
            'values': 'inline',
            'keyTimes': '0.0',
            'fill': 'remove'
        }
        frame.add(svgwrite.animate.Animate('display', **extra))
        dwg.add(frame)

    dwg.save()


def draw_screen(screen_buffer, font_size, group_id, line_size=80):
    frame = svgwrite.container.Group(id=group_id, display='none')
    # TODO: If a line is empty, is it missing from the buffer?
    for row in screen_buffer.keys():
        height = (font_size + 2) * (row + 1)
        text = svgwrite.text.Text('', y=[height], id=f'line_{row}')
        tspan_text = ''
        last_tspan_attributes = {}
        default_char = pyte.screens.Char(data=' ', fg='default', bg='default', bold=False,
                                         italics=False, underscore=False, strikethrough=False,
                                         reverse=False)

        # Empty screen cells are missing from the buffer so add them back as 'default_char'
        columns = screen_buffer[row].keys()
        if len(columns) == 0:
            whole_line_len = 0
        else:
            whole_line_len = min(line_size, max(columns) + 1)
        whole_line = [screen_buffer[row][col] if col in screen_buffer[row] else default_char
                      for col in range(whole_line_len)]

        for char in whole_line:
            tspan_attributes = {}
            # TODO: breaks with 256 colors
            # if char.fg != 'default':
            #     tspan_attributes['fill'] = char.fg
            if char.bold:
                tspan_attributes['style'] = 'font-weight:bold;'

            if tspan_attributes != last_tspan_attributes:
                if tspan_text:
                    tspan = svgwrite.text.TSpan(text=tspan_text, **last_tspan_attributes)
                    text.add(tspan)
                tspan_text = char.data
            else:
                tspan_text += char.data

            last_tspan_attributes = tspan_attributes

        if tspan_text:
            tspan = svgwrite.text.TSpan(text=tspan_text, **last_tspan_attributes)
            text.add(tspan)
            frame.add(text)

    return frame


if __name__ == '__main__':
    timings = record()
    squashed_timings = group_by_time(timings, threshold=datetime.timedelta(milliseconds=40))
    render_animation(squashed_timings, '/tmp/test.svg')

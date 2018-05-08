import os
import pty
import svgwrite
import svgwrite.text
import svgwrite.path
import svgwrite.animate
import svgwrite.container
import time
import datetime
#import cairo
import pyte

BUFFER_SIZE = 1040


# TODO: Get rid off Cairo dependence
# http://blog.mathieu-leplatre.info/text-extents-with-python-cairo.html
# def textwidth(text: str, font: str, fontsize: int) -> int:
#     surface = cairo.SVGSurface('undefined.svg', 1280, 200)
#     cr = cairo.Context(surface)
#     cr.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
#     cr.set_font_size(fontsize)
#     xbearing, ybearing, width, height, xadvance, yadvance = cr.text_extents(text)
#     return width


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
    print(b''.join(d for d, _ in timings))
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


def render_animation(timings, filename, end_pause=0.5):
    if end_pause < 0:
        raise ValueError('End pause duration must be greater than or equal to 0 seconds')

    font = 'Dejavu Sans Mono'
    font_size = 14
    style = f'font-family: {font}; font-style: normal; font-size: {font_size}px; white-space: pre;'
    dwg = svgwrite.Drawing(filename, (900, 900), debug=True, style=style)
    input_data, times = zip(*timings)
    duration = (times[-1] - times[0]).total_seconds()
    key_times = [(time - times[0]).total_seconds()/duration for time in times]

    counter = 0
    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)
    for bs, key_time in zip(input_data, key_times):
        stream.feed(bs)
        frame = draw_screen(screen.buffer, font_size, f'frame_{counter}')
        values = ['none'] * len(input_data)
        values[counter] = 'inline'

        # animation with duration == 0 won't work
        assert duration > 0
        extra = {
            'id': f'animation_{counter}',
            'begin': '0s',
            'dur': f'{duration:.3f}s',
            'values': ';'.join(values),
            'keyTimes': ';'.join(f'{t:.3f}' for t in key_times),
            'repeatCount': 'indefinite'
        }
        frame.add(svgwrite.animate.Animate('display', **extra))
        dwg.add(frame)
        counter += 1

    dwg.save()


def draw_screen(screen_buffer, font_size, group_id):
    frame = svgwrite.container.Group(id=group_id)
    for row in screen_buffer:
        height = (font_size + 2) * (row + 1)
        text = svgwrite.text.Text('', y=[height], id=row)
        tspan_text = ''
        last_tspan_attributes = {}
        for col in screen_buffer[row]:
            char = screen_buffer[row][col]
            print(f'char.data = "{char.data}"')
            tspan_attributes = {}
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


# def draw(lines, filename: str):
#     font = 'Dejavu Sans Mono'
#     font_size = 48
#     style = f'font-family: {font}; font-style: normal; font-size: {font_size}px;'
#     dwg = svgwrite.Drawing(filename, (900, 900), debug=True)
#     paragraph = dwg.add(dwg.g(style=style))
#     for counter, line in enumerate(lines):
#         partial_text = ''
#         animation = []
#         begin_time = line[0][1]
#         end_time = line[-1][1]
#         total_time = (end_time - begin_time).total_seconds()
#         row = 2 * font_size + counter * (font_size + 2)
#         for item, time in line:
#             if end_time == begin_time:
#                 # For discrete animations, the first value in the keyTimes list
#                 # must be 0 (SVG specification)
#                 keytime = 0.0
#             else:
#                 elapsed_time = (time - begin_time).total_seconds()
#                 keytime = elapsed_time / total_time
#
#             assert 0.0 <= keytime <= 1.0
#
#             print(partial_text)
#             partial_text = partial_text + item.decode('utf-8')
#             end = textwidth(partial_text, font, font_size)
#             d = f'm0,{row} h{end}'
#             animation.append((d, keytime))
#
#         values, keytimes = zip(*animation)
#
#         # duration must not be 0
#         extra = {
#             'begin': f'animation_{counter-1}.end' if counter > 0 else '0s',
#             'dur': f'{total_time}s' if total_time != 0 else '0.01s',
#             'fill': 'freeze',
#             'id': f'animation_{counter}',
#             'values': ';'.join(values),
#             'keyTimes': ';'.join(map(str, keytimes))
#         }
#         hidden_path = f'm0,{row} h0'
#         path = svgwrite.path.Path(d=hidden_path, id=f'path_{counter}')
#         path.add(svgwrite.animate.Animate('d', **extra))
#         paragraph.add(path)
#
#         text = svgwrite.text.Text('')
#         text.add(svgwrite.text.TextPath(path=path, text=partial_text))
#         paragraph.add(text)
#
#     dwg.save()


if __name__ == '__main__':
    timings = record()
    squashed_timings = group_by_time(timings, threshold=datetime.timedelta(milliseconds=40))
    render_animation(squashed_timings, '/tmp/test.svg')

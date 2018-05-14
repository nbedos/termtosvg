import datetime
from itertools import groupby
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
import selectors
import sys
import tty
from typing import Dict, Tuple, Generator, List, Callable
from Xlib import display, rdb, Xatom
from Xlib.error import DisplayError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

"""
Use case: Record a TERMINAL SESSION and RENDER it as an SVG ANIMATION. The idea
is to produce a short (<2 minutes) animation that can be showcased on a project page to
illustrate a use case.

RECORD a TERMINAL SESSION: CAPTURE input from the terminal session and save it together with both 
TIMINGS (when key are pressed or output is written to screen) and CONFIGURATION (how are 
colors rendered by the terminal, bold... etc). All this data will be used to replay the 
terminal session (since we captured the input of the session, not the output).

Once the terminal session has been replayed, it can be CONVERTED FRAME by frame to an 
SVG ANIMATION that mimicks the terminal session.

The terminal session should be SAVED so that it can be replayed and rendered with different
options at any time.

"""


class TerminalSession:
    """
    Record, save and replay a terminal session
    """
    def __init__(self):
        self.buffer_size = 1024
        self.colors = None

    def record(self, input_fileno=sys.stdin.fileno(), output_fileno=sys.stdout.fileno()):
        # type: (TerminalSession, int, int) -> Generator[Tuple[bytes, datetime.datetime], None, int]
        """Record raw input and output of a shell session

        This function forks the current process. The child process is a shell which is a session
        leader, has a controlling terminal and is run in the background. The parent process, which
        runs in the foreground, transmits data between the standard input, output and the shell
        process and logs it. From the user point of view, it appears they are communicating with
        their shell (through their terminal emulator) when in fact they communicate with our parent
        process which logs all the data exchanged with the shell

        Alternative file descriptors (filenos) can be passed to the function in replacement of
        the descriptors for the standard input and output

        The implementation of this method is mostly copied from the pty.spawn function of the
        CPython standard library. It has been modified in order to make the record function a
        generator.

        :param input_fileno: File descriptor of the input data stream
        :param output_fileno: File descriptor of the output data stream
        """
        shell = os.environ.get('SHELL', 'sh')

        pid, master_fd = pty.fork()
        if pid == 0:
            # Child process
            os.execlp(shell, shell)

        # Parent process
        try:
            mode = tty.tcgetattr(input_fileno)
            tty.setraw(input_fileno)
        except tty.error:
            mode = None

        sel = selectors.DefaultSelector()
        sel.register(master_fd, selectors.EVENT_READ)
        sel.register(input_fileno, selectors.EVENT_READ)

        while {master_fd, input_fileno} <= set(sel.get_map().keys()):
            events = sel.select()
            for key, _ in events:
                try:
                    data = os.read(key.fileobj, self.buffer_size)
                except OSError:
                    sel.unregister(key.fileobj)
                    break

                if not data:
                    sel.unregister(key.fileobj)
                    continue

                if key.fileobj == input_fileno:
                    while data:
                        n = os.write(master_fd, data)
                        data = data[n:]

                elif key.fileobj == master_fd:
                    os.write(output_fileno, data)
                    yield data, datetime.datetime.now()

        if mode is not None:
            tty.tcsetattr(input_fileno, tty.TCSAFLUSH, mode)

        os.close(master_fd)
        return os.waitpid(pid, 0)[1]

    def replay(self):
        """
        From the data gathered during a terminal record session, render the screen at each
        step of the session
        :return:
        """
        pass

    def get_configuration(self):
        """Get configuration information related to terminal output rendering"""
        xresources_str = self._get_xresources()
        self.colors = self._parse_xresources(xresources_str)

    @staticmethod
    def _get_xresources():
        # type: (...) -> str
        """Query the X server about the color configuration for the default display (Xresources)

        :return: Xresources as a string
        """
        try:
            d = display.Display()
            data = d.screen(0).root.get_full_property(Xatom.RESOURCE_MANAGER,
                                                      Xatom.STRING)
        except DisplayError as e:
            logger.debug(f'No color configuration could be gathered from the X display: {e}')
        else:
            if data:
                return data.value.decode('utf-8')
        return ''

    @staticmethod
    def _parse_xresources(xresources):
        # type: (str) -> Dict[str, str]
        """Parse the Xresources string and return a mapping between colors and their value

        :return: dictionary mapping the name of each color to its hexadecimal value ('#abcdef')
        """
        res_db = rdb.ResourceDB(string=xresources)

        mapping = {}
        names = ['foreground', 'background'] + [f'color{index}' for index in range(16)]
        for name in names:
            res_name = 'Svg.' + name
            res_class = res_name
            try:
                mapping[name] = res_db[res_name, res_class]
            except KeyError:
                pass

        return mapping

    @staticmethod
    def _group_by_time(timings, threshold: int=50):
        threshold = datetime.timedelta(milliseconds=threshold)
        current_string = []
        current_time = None
        for character, t in timings:
            if current_time is not None:
                assert t - current_time >= datetime.timedelta(seconds=0)
                if t - current_time > threshold:
                    # Flush current string
                    s = b''.join(current_string)
                    yield s, current_time
                    current_string = []
                    current_time = t
            else:
                current_time = t

            current_string.append(character)

        if current_string:
            yield b''.join(current_string), current_time



class AsciiAnimation:
    """
    Feed on a set of ASCII screens and convert them to SVG frames
    """
    def __init__(self):
        pass

    def _render_line_bg_colors(self, screen_line, height, line_height):
        # type: (AsciiAnimation, Dict[int, pyte.screens.Char], float, float) -> List[svgwrite.shapes.Rect]
        def bgcolor(char: pyte.screens.Char) -> str:
            if char.reverse:
                if char.fg == 'default':
                    color = 'foreground'
                else:
                    color = char.fg
            else:
                if char.bg == 'default':
                    color = 'background'
                else:
                    color = char.bg
            return color

        def make_rectangle(group: List[int]) -> svgwrite.shapes.Rect:
            x = f'{group[0]}ex'
            y = f'{height:.2f}em'
            sx = f'{len(group)}ex'
            sy = f'{line_height:.2f}em'
            args = {
                'insert': (x, y),
                'size': (sx, sy),
                'class': bgcolor(screen_line[group[0]])
            }
            return svgwrite.shapes.Rect(**args)

        group = []
        groups = []
        for index in sorted(screen_line):
            group.append(index)
            if index + 1 not in screen_line or bgcolor(screen_line[index]) != bgcolor(screen_line[index + 1]):
                if bgcolor(screen_line[index]) != 'background':
                    groups.append(group)
                group = []

        rectangles = [make_rectangle(group) for group in groups]
        return rectangles

    # TODO: Merge rectangles over multiple lines
    def _render_frame_bg_colors(self, screen_buffer, line_height):
        # type: (AsciiAnimation, Dict[int, Dict[int, pyte.screens.Char]], float, str) -> List[svgwrite.shapes.Rect]
        rects = []
        for row in screen_buffer:
            height = row * line_height + 0.25
            rects += self._render_line_bg_colors(screen_buffer[row], height, line_height)
        return rects

    def _render_characters(self, screen_buffer, height_func):
        # type: (AsciiAnimation, List[Tuple[Tuple[int, int], pyte.screens.Char]], Callable[[int], float]) -> List[svgwrite.text.Text]
        """Render a screen of the terminal as a list of SVG text elements

        Characters with the same attributes (color, font weight) are grouped together in a
        single text element.

        :param screen_buffer: Mapping between positions on the screen (tuple row, column) and
        characters
        :param height_func: Function returning the vertical position of the text element
        from the row of the character in the buffer
        :return: List of SVG text elements
        """
        def char_attributes(item):
            _, char = item
            if char.reverse:
                if char.bg == 'default':
                    color = 'background'
                else:
                    color = char.bg
            else:
                if char.fg == 'default':
                    color = 'foreground'
                else:
                    color = char.fg
            return color, char.bold

        svg_items = []
        sorted_chars = sorted(screen_buffer, key=char_attributes)
        for attributes, group in groupby(sorted_chars, char_attributes):
            color, bold = attributes
            text_attributes = {}
            classes = []
            if color != 'foreground':
                classes.append(color)
            if bold:
                classes.append('bold')

            if classes:
                text_attributes['class'] = ' '.join(classes)

            group_chars = [(index, (char.data if char.data != ' ' else u'\u00A0'))
                           for index, char in group]

            text = ''.join(c for _, c in group_chars)
            xs = [f'{col}ex' for (row, col), _ in group_chars]
            ys = [f'{height_func(row):.2f}em' for (row, col), _ in group_chars]
            text = svgwrite.text.Text(text=text, x=xs, y=ys, **text_attributes)

            svg_items.append(text)

        return svg_items

    def _render_frame_fg(self, screen_buffer, line_height, group_id):
        # type: (AsciiAnimation, Dict[int, Dict[int, pyte.screens.Char]], float, str) -> svgwrite.container.Group
        def height_func(row: int) -> float:
            return (row + 1) * line_height

        frame = svgwrite.container.Group(id=group_id)
        all_chars = [((row, col), screen_buffer[row][col])
                     for row in sorted(screen_buffer)
                     for col in sorted(screen_buffer[row])]
        svg_items = self._render_characters(all_chars, height_func=height_func)
        for item in svg_items:
            frame.add(item)
        return frame

    def _render_frame(self):
        pass

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
            rects = self._render_frame_bg_colors(screen.buffer, line_height)
            for rect in rects:
                frame.add(rect)

            # Foreground
            frame_fg = self._render_frame_fg(screen.buffer, line_height, f'frame_fg_{index}')
            frame.add(frame_fg)

            # Animation
            try:
                frame_duration = (times[index + 1] - times[index]).total_seconds()
            except IndexError:
                frame_duration = end_pause

            frame_duration_str = f'{frame_duration:.3f}s'
            assert frame_duration != '0.000s'
            extra = {
                'id': f'animation_{index}',
                'begin': f'animation_{index-1}.end' if index > 0 else first_animation_begin,
                'dur': frame_duration_str,
                'values': 'inline;inline',
                'keyTimes': '0.0;1.0',
                'fill': 'remove'
            }
            frame.add(svgwrite.animate.Animate('display', **extra))
            dwg.add(frame)

        dwg.save()

    @staticmethod
    def _serialize_css_dict(css):
        # type: (Dict[str, Dict[str, str]]) -> str
        def serialize_css_item(item):
            return '; '.join(f'{prop}: {item[prop]}' for prop in item)

        items = [f'{item} {{{serialize_css_item(css[item])}}}' for item in css]
        return os.linesep.join(items)

if __name__ == '__main__':
    t = TerminalSession()
    t.get_configuration()
    timings = t.record()
    squashed_timings = t._group_by_time(timings)

    a = AsciiAnimation()
    a.render_animation(squashed_timings, '/tmp/test.svg', t.colors)

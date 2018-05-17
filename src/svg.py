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
from typing import Dict, Tuple, Generator, List, Iterable, Any, Union
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

# TODO: CSS default attribute for <text> all x positions
# TODO: Since we're not using textLength after all, go back to one line = one <text> (+ <tspan>s)
# TODO: Group lines with the same timings in a single group with a unique animation
# TODO: Remove frame rendering code
# TODO: AsciiBuffer type (based on mappings)
# TODO: Use viewbox to render a portion of the history
# TODO: Save session in asciinema v2 format
# TODO: Use screen buffer difference for cell targeted updating, or just use screen.dirty from pyte


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

        while {master_fd, input_fileno} <= set(sel.get_map()):
            events = sel.select()
            for key, _ in events:
                try:
                    data = os.read(key.fileobj, self.buffer_size)
                except OSError:
                    sel.unregister(key.fileobj)
                    continue

                if not data:
                    sel.unregister(key.fileobj)
                    continue

                if key.fileobj == input_fileno:
                    write_fileno = master_fd
                else:
                    write_fileno = output_fileno
                    yield data, datetime.datetime.now()

                while data:
                    n = os.write(write_fileno, data)
                    data = data[n:]

        if mode is not None:
            tty.tcsetattr(input_fileno, tty.TCSAFLUSH, mode)

        os.close(master_fd)

        _, child_exit_status = os.waitpid(pid, 0)
        return child_exit_status

    @staticmethod
    def _group_by_time(timings, min_frame_duration=50, last_frame_duration=1000):
        # type: (Iterable[Tuple[bytes, datetime.datetime]], int, int) -> Generator[Tuple[bytes, datetime.timedelta], None, None]
        """Group frames together so that any frame duration is greater than min_frame_duration

        :param timings: Sequence of bytestrings associated with the time they were received
        :param min_frame_duration: Minimum frame duration in milliseconds
        :param last_frame_duration: Last frame duration in milliseconds
        :return: Sequence of bytestrings associated with the time before the next bytes were
        received
        """
        min_frame_duration = datetime.timedelta(milliseconds=min_frame_duration)
        current_string = []
        current_time = None
        for character, time in timings:
            if current_time is not None:
                duration = time - current_time
                if duration < datetime.timedelta(seconds=0):
                    raise ValueError('Data must be chronologically sorted')
                elif duration >= min_frame_duration:
                    # Flush current string
                    s = b''.join(current_string)
                    yield s, duration
                    current_string = []
                    current_time = time
            else:
                current_time = time

            current_string.append(character)

        if current_string:
            last_frame_duration = datetime.timedelta(milliseconds=last_frame_duration)
            yield b''.join(current_string), last_frame_duration

    def replay(self, timings):
        # type: (TerminalSession, Iterable[Tuple[bytes, datetime.datetime]]) -> Generator[Tuple[Dict[int, Dict[int, AsciiChar]], datetime.timedelta], None, None]
        """
        Render screens of the terminal session after having grouped frames by time
        """
        screen = pyte.Screen(80, 24)
        stream = pyte.ByteStream(screen)
        for data, time in TerminalSession._group_by_time(timings):
            stream.feed(data)
            ascii_buffer = {}
            for row in screen.buffer:
                ascii_buffer[row] = {}
                for column in screen.buffer[row]:
                    char = screen.buffer[row][column]
                    ascii_buffer[row][column] = TerminalSession.pyte_to_ascii(char)

            yield ascii_buffer, time

    @staticmethod
    def pyte_to_ascii(char):
        # type: (pyte.screens.Char) -> AsciiChar
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

        if char.fg == 'default':
            text_color = 'foreground'
        elif char.fg in colors:
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
                id = f'animation_{row}_{row_animations[row]+1}'
                row_animations[row] += 1
            else:
                begin = f'{current_time.total_seconds():.3f}s'
                id = f'animation_{row}_0'
                row_animations[row] = 0

            extra = {
                'id': id,
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


if __name__ == '__main__':
    t = TerminalSession()
    t.get_configuration()
    timings = t.record()
    squashed_timings = t.replay(timings)

    a = AsciiAnimation()
    line_timings = a._line_timings(squashed_timings)
    a.render_animation(line_timings, '/tmp/test.svg', t.colors)

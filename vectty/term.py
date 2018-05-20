import datetime
import fcntl
import logging
import os
import pty
import selectors
import struct
import sys
import termios
import tty
from typing import Dict, Tuple, Generator, Iterable, Any

import pyte
import pyte.screens
from Xlib import display, rdb, Xatom
from Xlib.error import DisplayError

from vectty.anim import AsciiChar

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class _TerminalMode:
    """Save and restore terminal state"""
    def __init__(self, fileno: int):
        self.fileno = fileno
        self.mode = None

    def __enter__(self):
        try:
            self.mode = tty.tcgetattr(self.fileno)
            tty.setraw(self.fileno)
        except tty.error:
            pass
        return self.mode

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.mode is not None:
            tty.tcsetattr(self.fileno, tty.TCSAFLUSH, self.mode)


class TerminalSession:
    """
    Record, save and replay a terminal session
    """
    def __init__(self):
        self.buffer_size = 1024
        self.colors = None
        self.lines = None
        self.columns = None

        self.get_configuration()

    def record(self):
        # type: (...) -> Generator[Dict[str, Any], None, None]
        """
        Record a terminal session in asciicast v2 format

        The records returned are of two types:
            - a single header with configuration information
            - multiple event records with data captured from the terminal with timing information

        Format specification: https://github.com/asciinema/asciinema/blob/develop/doc/asciicast-v2.md
        """

        header = {
            'version': 2,
            'width': self.columns,
            'height': self.lines
        }

        try:
            header['theme'] = {
                'fg': self.colors['foreground'],
                'bg': self.colors['background'],
                'palette': ':'.join(self.colors[f'color{i}'] for i in range(16))
            }
        except KeyError:
            pass

        yield header

        start = None
        for data, time in self._record(output_fileno=sys.stdout.fileno()):
            if start is None:
                start = time

            record = {
                'time': (time - start).total_seconds(),
                'event-type': 'o',
                'event-data': data
            }

            yield record

    def _record(self, input_fileno=sys.stdin.fileno(), output_fileno=sys.stdout.fileno()):
        # type: (int, int) -> Generator[Tuple[bytes, datetime.datetime], None, int]
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
        See https://github.com/python/cpython/blob/master/Lib/pty.py

        :param input_fileno: File descriptor of the input data stream
        :param output_fileno: File descriptor of the output data stream
        """
        shell = os.environ.get('SHELL', 'sh')

        pid, master_fd = pty.fork()
        if pid == 0:
            # Child process
            os.execlp(shell, shell)

        # Set the terminal size for master_fd
        ttysize = struct.pack("HHHH", self.lines, self.columns, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, ttysize)

        # Parent process
        with _TerminalMode(input_fileno):
            for data, time in self._capture_data(input_fileno, output_fileno, master_fd):
                yield data, time

        os.close(master_fd)

        _, child_exit_status = os.waitpid(pid, 0)
        return child_exit_status

    def _capture_data(self, input_fileno, output_fileno, master_fd):
        # type: (int, int, int) -> Generator[bytes, datetime.datetime]
        """
        Data from input_fileno is sent to master_fd
        Data from master_fd is both sent to output_fileno and returned to the caller

        The implementation of this method is mostly copied from the pty.spawn function of the
        CPython standard library. It has been modified in order to make the record function a
        generator.
        See https://github.com/python/cpython/blob/master/Lib/pty.py
        """
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

    @staticmethod
    def _group_by_time(records, min_frame_duration=0.050, last_frame_duration=1.000):
        # type: (Iterable[Dict[str, Any]], float, float) -> Generator[Dict[str, Any], None, None]
        """Compute frame duration and group frames together so that the minimum duration of
        any frame is at most min_frame_duration

        :param records: Sequence of records (asciicast v2 format)
        :param min_frame_duration: Minimum frame duration in seconds
        :param last_frame_duration: Last frame duration in seconds
        :return: Sequence of records with the added attribute 'duration'
        """
        current_string = b''
        current_time = None

        for record in records:
            # Skip header
            if 'version' in record:
                yield record
                continue

            if current_time is not None:
                time_between_events = record['time'] - current_time
                if time_between_events >= min_frame_duration:
                    # Flush current string
                    yield {
                        'time': current_time,
                        'event-type': 'o',
                        'event-data': current_string,
                        'duration': time_between_events
                    }
                    current_string = b''
                    current_time = record['time']
            else:
                current_time = record['time']

            current_string += record['event-data']

        if current_string:
            yield {
                'time': current_time,
                'event-type': 'o',
                'event-data': current_string,
                'duration': last_frame_duration
            }

    def replay(self, asciicast_records, min_frame_duration=0.05):
        # type: (Iterable[Dict[str, Any]], float) -> Generator[Tuple[int, Dict[int, AsciiChar], float, float], None, None]
        """
        Return lines of the screen that need updating. Frames are merged together so that there is
        at least a 'min_frame_duration' seconds pause between two frames.

        Lines returned are sorted by time of appearance on the screen and duration of the appearance
        so that they can be grouped together in the same frame or animation

        :param asciicast_records: Event record in asciicast v2 format
        :param min_frame_duration: Minimum frame duration in seconds
        :return: Tuples consisting of:
            - Row number of the line on the screen
            - Line
            - Time when this line appears on the screen in seconds this the beginning of ther terminal
            session
            - Duration of this lines on the screen in seconds
        """
        def sort_by_time(d, row):
            line, line_time, line_duration = d[row]
            return line_time, line_duration, row

        screen = pyte.Screen(self.columns, self.lines)
        stream = pyte.ByteStream(screen)
        pending_lines = {}
        current_time = 0
        for record in TerminalSession._group_by_time(asciicast_records, min_frame_duration):
            if 'version' in record or record['event-type'] != 'o':
                continue

            stream.feed(record['event-data'])
            ascii_buffer = {
                row: {
                    column: TerminalSession.pyte_to_ascii(screen.buffer[row][column])
                    for column in screen.buffer[row]
                } for row in screen.dirty
            }

            screen.dirty.clear()

            duration = record['duration']
            done_lines = {}
            for row in pending_lines:
                line, line_time, line_duration = pending_lines[row]
                if row in ascii_buffer:
                    done_lines[row] = line, line_time, line_duration
                else:
                    pending_lines[row] = line, line_time, line_duration + duration

            for row in ascii_buffer:
                if ascii_buffer[row]:
                    pending_lines[row] = ascii_buffer[row], current_time, duration
                elif row in pending_lines:
                    del pending_lines[row]

            for row in sorted(done_lines, key=lambda row: sort_by_time(done_lines, row)):
                yield row, done_lines[row][0], done_lines[row][1], done_lines[row][2]

            current_time += duration

        for row in sorted(pending_lines, key=lambda row: sort_by_time(pending_lines, row)):
            yield row, pending_lines[row][0], pending_lines[row][1], pending_lines[row][2]

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
        try:
            self.columns, self.lines = os.get_terminal_size(sys.stdout.fileno())
        except OSError as e:
            self.lines = 24
            self.columns = 80
            logger.debug(f'Failed to get terminal size ({e}), '
                         f'using default values instead ({self.columns}x{self.lines})')

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

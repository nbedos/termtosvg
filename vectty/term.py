import datetime
import logging
import os
import pty
import pyte
import pyte.screens
import selectors
import sys
import tty
from typing import Dict, Tuple, Generator, Iterable
from Xlib import display, rdb, Xatom
from Xlib.error import DisplayError

from vectty.anim import AsciiChar

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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
            print("terminal restored")

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

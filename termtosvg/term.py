import datetime
import fcntl
import logging
import os
import pty
import selectors
import struct
import termios
import tty
from copy import copy
from functools import partial
from typing import Any, Callable, Dict, Generator, Iterable, Iterator, Tuple, Union

import pyte
import pyte.screens

from termtosvg.anim import CharacterCellConfig, CharacterCellLineEvent, CharacterCellRecord
from termtosvg.asciicast import AsciiCastV2Event, AsciiCastV2Header, AsciiCastV2Theme

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TerminalMode:
    """Save terminal state on entry, restore it on exit"""
    def __init__(self, fileno: int):
        self.fileno = fileno
        self.mode = None

    def __enter__(self):
        try:
            self.mode = tty.tcgetattr(self.fileno)
        except tty.error:
            pass
        return self.mode

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.mode is not None:
            tty.tcsetattr(self.fileno, tty.TCSAFLUSH, self.mode)


def record(columns, lines, input_fileno, output_fileno):
    # type: (int, int, int, int) -> Generator[Union[AsciiCastV2Header, AsciiCastV2Event], None, None]
    """Record a terminal session in asciicast v2 format

    The records returned are of two types:
        - a single header with configuration information
        - multiple event records with data captured from the terminal and timing information
    """
    yield AsciiCastV2Header(version=2, width=columns, height=lines, theme=None)

    start = None
    for data, time in _record(columns, lines, input_fileno, output_fileno):
        if start is None:
            start = time

        yield AsciiCastV2Event(time=(time - start).total_seconds(),
                               event_type='o',
                               event_data=data,
                               duration=None)


def _record(columns, lines, input_fileno, output_fileno):
    # type: (int, int, int, int) -> Generator[Tuple[bytes, datetime.datetime], None, int]
    """Record raw input and output of a shell session

    This function forks the current process. The child process is a shell which is a session
    leader and has a controlling terminal and is run in the background. The parent process, which
    runs in the foreground, transmits data between the standard input, output and the shell
    process and logs it. From the user point of view, it appears they are communicating with
    their shell (through their terminal emulator) when in fact they communicate with our parent
    process which logs all the data exchanged with the shell

    The implementation of this method is mostly copied from the pty.spawn function of the
    CPython standard library. It has been modified in order to make the record function a
    generator.
    See https://github.com/python/cpython/blob/master/Lib/pty.py

    :param columns: Initial number of columns of the terminal
    :param lines: Initial number of lines of the terminal
    :param input_fileno: File descriptor of the input data stream
    :param output_fileno: File descriptor of the output data stream
    """
    shell = os.environ.get('SHELL', 'sh')

    pid, master_fd = pty.fork()
    if pid == 0:
        # Child process
        os.execlp(shell, shell)

    # Set the terminal size for master_fd
    ttysize = struct.pack("HHHH", lines, columns, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, ttysize)

    # Parent process
    try:
        tty.setraw(input_fileno)
    except tty.error:
        pass

    for data, time in _capture_data(input_fileno, output_fileno, master_fd):
        yield data, time

    os.close(master_fd)

    _, child_exit_status = os.waitpid(pid, 0)
    return child_exit_status


def _capture_data(input_fileno, output_fileno, master_fd, buffer_size=1024):
    # type: (int, int, int, int) -> Generator[bytes, datetime.datetime]
    """Send data from input_fileno to master_fd and send data from master_fd to output_fileno and
    also return it to the caller

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
                data = os.read(key.fileobj, buffer_size)
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


def _group_by_time(event_records, min_rec_duration, last_rec_duration):
    # type: (Iterable[AsciiCastV2Event], float, float) -> Generator[AsciiCastV2Event, None, None]
    """Merge event records together if they are close enough and compute the duration between
    consecutive events. The duration between two consecutive event records returned by the function
    is guaranteed to be at least min_rec_duration.

    :param event_records: Sequence of records in asciicast v2 format
    :param min_rec_duration: Minimum time between two records returned by the function in seconds.
    This helps avoiding 0s duration animations which break SVG animations.
    :param last_rec_duration: Duration of the last record in seconds
    :return: Sequence of records
    """
    current_string = b''
    current_time = None

    for event_record in event_records:
        if event_record.event_type != 'o':
            continue

        if current_time is not None:
            time_between_events = event_record.time - current_time
            if time_between_events >= min_rec_duration:
                accumulator_event = AsciiCastV2Event(time=current_time,
                                                     event_type='o',
                                                     event_data=current_string,
                                                     duration=time_between_events)
                yield accumulator_event
                current_string = b''
                current_time = event_record.time
        else:
            current_time = event_record.time

        current_string += event_record.event_data

    if current_string:
        accumulator_event = AsciiCastV2Event(time=current_time,
                                             event_type='o',
                                             event_data=current_string,
                                             duration=last_rec_duration)
        yield accumulator_event


def replay(records, from_pyte_char, override_theme, fallback_theme, min_frame_duration=0.001, last_frame_duration=1):
    # type: (Iterable[Union[AsciiCastV2Header, AsciiCastV2Event]], Callable[[pyte.screen.Char, Dict[Any, str]], Any], Union[None, AsciiCastV2Theme], AsciiCastV2Theme, float, float) -> Generator[CharacterCellRecord, None, None]
    """Read the records of a terminal sessions, render the corresponding screens and return lines
    of the screen that need updating.

    Records are merged together so that there is at least a 'min_frame_duration' seconds pause
    between two rendered screens.
    Lines returned are sorted by time and duration of their appearance on the screen so that lines
    in need of updating at the same time can easily be grouped together.
    The terminal screen is rendered using Pyte and then each character of the screen is converted
    to the caller's format of choice using from_pyte_char

    :param records: Records of the terminal session in asciicast v2 format. The first record must
    be a header, which must be followed by event records.
    :param from_pyte_char: Conversion function from pyte.screen.Char to any other format
    :param override_theme: Color theme. If present, overrides the theme include in asciicast header
    :param fallback_theme: Color theme. Used as a fallback override_theme is missing and no
    theme is included in asciicast header
    :param min_frame_duration: Minimum frame duration in seconds. SVG animations break when an
    animation is 0s so setting this to at least 1ms is recommended.
    :param last_frame_duration: Last frame duration in seconds
    :return: Records in the CharacterCellRecord format:
        1/ a header with configuration information (CharacterCellConfig)
        2/ one event record for each line of the screen that need to be redrawn (CharacterCellLineEvent)
    """
    def sort_by_time(d, row):
        row_line, row_line_time, row_line_duration = d[row]
        return row_line_time + row_line_duration, row

    if not isinstance(records, Iterator):
        records = iter(records)

    header = next(records)
    screen = pyte.Screen(header.width, header.height)
    stream = pyte.ByteStream(screen)

    if override_theme is not None:
        theme = override_theme
    elif header.theme is not None:
        theme = header.theme
    else:
        theme = fallback_theme

    config = CharacterCellConfig(width=header.width,
                                 height=header.height,
                                 text_color=theme.fg,
                                 background_color=theme.bg)
    yield config

    palette = {
        'foreground': theme.fg,
        'background': theme.bg
    }
    palette.update(enumerate(theme.palette.split(':')))

    pending_lines = {}
    current_time = 0
    last_cursor = None
    for event_record in _group_by_time(records, min_frame_duration, last_frame_duration):
        stream.feed(event_record.event_data)

        # Numbers of lines that must be redrawn
        dirty_lines = set(screen.dirty)
        if screen.cursor != last_cursor:
            # Line where the cursor will be drawn
            dirty_lines.add(screen.cursor.y)
            if last_cursor is not None:
                # Line where the cursor will be erased
                dirty_lines.add(last_cursor.y)

        redraw_buffer = {}
        for row in dirty_lines:
            redraw_buffer[row] = {}
            for column in screen.buffer[row]:
                redraw_buffer[row][column] = from_pyte_char(screen.buffer[row][column], palette)

        if screen.cursor != last_cursor:
            try:
                data = screen.buffer[screen.cursor.y][screen.cursor.x].data
            except KeyError:
                data = ' '

            cursor_char = pyte.screens.Char(data=data,
                                            fg=screen.cursor.attrs.fg,
                                            bg=screen.cursor.attrs.bg,
                                            reverse=True)
            redraw_buffer[screen.cursor.y][screen.cursor.x] = from_pyte_char(cursor_char, palette)

        last_cursor = copy(screen.cursor)
        screen.dirty.clear()

        completed_lines = {}
        # Conversion from seconds to milliseconds
        duration = int(1000 * round(event_record.duration, 3))
        for row in pending_lines:
            line, line_time, line_duration = pending_lines[row]
            if row in redraw_buffer:
                completed_lines[row] = line, line_time, line_duration
            else:
                pending_lines[row] = line, line_time, line_duration + duration

        for row in redraw_buffer:
            if redraw_buffer[row]:
                pending_lines[row] = redraw_buffer[row], current_time, duration
            elif row in pending_lines:
                del pending_lines[row]

        for row in sorted(completed_lines, key=partial(sort_by_time, completed_lines)):
            args = (row, *completed_lines[row])
            yield CharacterCellLineEvent(*args)

        current_time += duration

    for row in sorted(pending_lines, key=partial(sort_by_time, pending_lines)):
        args = (row, *pending_lines[row])
        yield CharacterCellLineEvent(*args)


def get_terminal_size(fileno):
    # type: (int) -> (int, int)
    try:
        columns, lines = os.get_terminal_size(fileno)
    except OSError as e:
        lines = 24
        columns = 80
        logger.debug('Failed to get terminal size ({}), using default values '
                     'instead ({}x{})'.format(e, columns, lines))

    return columns, lines

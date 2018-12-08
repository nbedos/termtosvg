import datetime
import fcntl
import os
import pty
import select
import struct
import termios
import tty
from copy import copy
from functools import partial
from typing import Iterator

import pyte
import pyte.screens

from termtosvg.anim import CharacterCellConfig, CharacterCellLineEvent
from termtosvg.asciicast import AsciiCastV2Event, AsciiCastV2Header


class TerminalMode:
    """Save terminal mode and size on entry, restore them on exit"""
    def __init__(self, fileno: int):
        self.fileno = fileno
        self.mode = None
        self.ttysize = None

    def __enter__(self):
        try:
            self.mode = tty.tcgetattr(self.fileno)
        except tty.error:
            pass

        try:
            columns, lines = os.get_terminal_size(self.fileno)
        except OSError:
            pass
        else:
            self.ttysize = struct.pack("HHHH", lines, columns, 0, 0)

        return self.mode, self.ttysize

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.ttysize is not None:
            fcntl.ioctl(self.fileno, termios.TIOCSWINSZ, self.ttysize)

        if self.mode is not None:
            tty.tcsetattr(self.fileno, tty.TCSAFLUSH, self.mode)


def record(process_args, columns, lines, input_fileno, output_fileno):
    """Record a process in asciicast v2 format

    The records returned are of two types:
        - a single header with configuration information
        - multiple event records with data captured from the terminal and timing information
    """
    yield AsciiCastV2Header(version=2, width=columns, height=lines, theme=None)

    start = None
    for data, time in _record(process_args, columns, lines, input_fileno, output_fileno):
        if start is None:
            start = time

        yield AsciiCastV2Event(time=(time - start).total_seconds(),
                               event_type='o',
                               event_data=data,
                               duration=None)


def _record(process_args, columns, lines, input_fileno, output_fileno):
    """Record raw input and output of a process

    This function forks the current process. The child process runs the command specified by
    'process_args' which is a session leader and has a controlling terminal and is run in the
    background. The parent process, which runs in the foreground, transmits data between the
    standard input, output and the child process and logs it. From the user point of view, it
    appears they are communicating with the process they intend to record (through their terminal
    emulator) when in fact they communicate with our parent process which logs all data exchanges
    with the user

    The implementation of this method is mostly copied from the pty.spawn function of the
    CPython standard library. It has been modified in order to make the record function a
    generator.
    See https://github.com/python/cpython/blob/master/Lib/pty.py

    :param process_args: List of arguments to run the process to be recorded
    :param columns: Initial number of columns of the terminal
    :param lines: Initial number of lines of the terminal
    :param input_fileno: File descriptor of the input data stream
    :param output_fileno: File descriptor of the output data stream
    """
    pid, master_fd = pty.fork()
    if pid == 0:
        # Child process - this call never returns
        os.execlp(process_args[0], *process_args)

    # Parent process
    # Set the terminal size for master_fd
    ttysize = struct.pack("HHHH", lines, columns, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, ttysize)

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
    """Send data from input_fileno to master_fd and send data from master_fd to output_fileno and
    also return it to the caller

    The implementation of this method is mostly copied from the pty.spawn function of the
    CPython standard library. It has been modified in order to make the record function a
    generator.
    See https://github.com/python/cpython/blob/master/Lib/pty.py
    """
    rlist = [input_fileno, master_fd]
    xlist = [input_fileno, output_fileno, master_fd]

    xfds = []
    while not xfds:
        rfds, _, xfds = select.select(rlist, [], xlist)
        for fd in rfds:
            try:
                data = os.read(fd, buffer_size)
            except OSError:
                xfds.append(fd)
                continue

            if not data:
                xfds.append(fd)
                continue

            if fd == input_fileno:
                write_fileno = master_fd
            else:
                write_fileno = output_fileno
                yield data, datetime.datetime.now()

            while data:
                n = os.write(write_fileno, data)
                data = data[n:]


def _group_by_time(event_records, min_rec_duration, max_rec_duration, last_rec_duration):
    """Merge event records together if they are close enough and compute the duration between
    consecutive events. The duration between two consecutive event records returned by the function
    is guaranteed to be at least min_rec_duration.

    :param event_records: Sequence of records in asciicast v2 format
    :param min_rec_duration: Minimum time between two records returned by the function in
    milliseconds. This helps avoiding 0s duration animations which break SVG animations.
    :param max_rec_duration: Limit of the time elapsed between two records
    :param last_rec_duration: Duration of the last record in milliseconds
    :return: Sequence of records
    """
    current_string = b''
    current_time = 0
    dropped_time = 0

    for event_record in event_records:
        if event_record.event_type != 'o':
            continue

        time_between_events = event_record.time - (current_time + dropped_time)
        if time_between_events * 1000 >= min_rec_duration:
            if max_rec_duration:
                if max_rec_duration / 1000 < time_between_events:
                    dropped_time += time_between_events - (max_rec_duration / 1000)
                    time_between_events = max_rec_duration / 1000
            accumulator_event = AsciiCastV2Event(time=current_time,
                                                 event_type='o',
                                                 event_data=current_string,
                                                 duration=time_between_events)
            yield accumulator_event
            current_string = b''
            current_time += time_between_events

        current_string += event_record.event_data

    if current_string:
        accumulator_event = AsciiCastV2Event(time=current_time,
                                             event_type='o',
                                             event_data=current_string,
                                             duration=last_rec_duration / 1000)
        yield accumulator_event


def replay(records, from_pyte_char, min_frame_duration, max_frame_duration, last_frame_duration=1000):
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
    :param min_frame_duration: Minimum frame duration in milliseconds. SVG animations break when
    an animation duration is 0ms so setting this to at least 1ms is recommended.
    :param max_frame_duration: Maximum duration of a frame in milliseconds. This is meant to limit
    idle time during a recording.
    :param last_frame_duration: Last frame duration in milliseconds
    :return: Records in the CharacterCellRecord format:
        1/ a header with configuration information (CharacterCellConfig)
        2/ one event record for each line of the screen that need to be redrawn
        (CharacterCellLineEvent)
    """
    def sort_by_time(d, row):
        _, row_line_time, row_line_duration = d[row]
        return row_line_time + row_line_duration, row

    if not isinstance(records, Iterator):
        records = iter(records)

    header = next(records)

    screen = pyte.Screen(header.width, header.height)
    stream = pyte.ByteStream(screen)
    if not max_frame_duration and header.idle_time_limit:
        max_frame_duration = int(header.idle_time_limit * 1000)

    yield CharacterCellConfig(header.width, header.height)

    pending_lines = {}
    current_time = 0
    last_cursor = None
    event_records = _group_by_time(records, min_frame_duration, max_frame_duration,
                                   last_frame_duration)
    for event_record in event_records:
        stream.feed(event_record.event_data)

        # Numbers of lines that must be redrawn
        dirty_lines = set(screen.dirty)
        if screen.cursor != last_cursor:
            # Line where the cursor will be drawn
            if not screen.cursor.hidden:
                dirty_lines.add(screen.cursor.y)
            if last_cursor is not None and not last_cursor.hidden:
                # Line where the cursor will be erased
                dirty_lines.add(last_cursor.y)

        redraw_buffer = {}
        for row in dirty_lines:
            redraw_buffer[row] = {}
            for column in screen.buffer[row]:
                redraw_buffer[row][column] = from_pyte_char(screen.buffer[row][column])

        if screen.cursor != last_cursor and not screen.cursor.hidden:
            try:
                data = screen.buffer[screen.cursor.y][screen.cursor.x].data
            except KeyError:
                data = ' '

            cursor_char = pyte.screens.Char(data=data,
                                            fg=screen.cursor.attrs.fg,
                                            bg=screen.cursor.attrs.bg,
                                            reverse=True)
            redraw_buffer[screen.cursor.y][screen.cursor.x] = from_pyte_char(cursor_char)

        last_cursor = copy(screen.cursor)
        screen.dirty.clear()

        completed_lines = {}
        duration = int(1000 * event_record.duration)
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
    try:
        columns, lines = os.get_terminal_size(fileno)
    except OSError:
        columns, lines = 80, 24

    return columns, lines

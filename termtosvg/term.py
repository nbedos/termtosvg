"""UNIX terminal recording functionalities

This module exposes functions for
    - recording the output of a shell process in asciicast v2 format (`record`)
    - reporting updates made to the screen during a terminal session that
    was recorded (`screen_events`)

A context manager named `TerminalMode` is also provided and is to be used with
the `record` function to ensure that the terminal state is always properly
restored, otherwise a failure during a call to `record` could render the
terminal unusable.
"""

import codecs
import datetime
import fcntl
import os
import pty
import select
import struct
import termios
import tty
from copy import copy
from collections import defaultdict, namedtuple
from typing import Iterator

import pyte
import pyte.screens

from termtosvg import anim
from termtosvg.asciicast import AsciiCastV2Event, AsciiCastV2Header


def _cursor___eq__(self, other):
    # TODO: See if upstream is interested in incorparating this
    attributes = ['x', 'y', 'hidden']
    return (isinstance(other, self.__class__) and
            all(self.__getattribute__(a) == other.__getattribute__(a)
                for a in attributes))


# Monkey patch equality operator so that we can detect changes of a cursor
pyte.screens.Cursor.__eq__ = _cursor___eq__


class TerminalMode:
    """Save terminal mode and size on entry, restore them on exit

    This context manager exists to ensure that the state of the terminal is
    properly restored when functions like `_record` (which relies on setting
    the terminal mode to raw and changing the geometry of the screen) fail.
    """
    def __init__(self, fileno):
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


def _record(process_args, columns, lines, input_fileno, output_fileno):
    """Record raw input and output of a process

    This function forks the current process. The child process runs the command
    specified by 'process_args' which is a session leader and has a controlling
    terminal and is run in the background. The parent process, which runs in
    the foreground, transmits data between the standard input, output and the
    child process and logs it. From the user point of view, it appears they are
    communicating with the process they intend to record (through their
    terminal emulator) when in fact they communicate with our parent process
    which logs all data exchanges with the user

    The implementation of this method is mostly copied from the pty.spawn
    function of the CPython standard library. It has been modified in order to
    make the record function a generator.
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

    for data, time in _capture_output(input_fileno, output_fileno, master_fd):
        yield data, time

    os.close(master_fd)

    _, child_exit_status = os.waitpid(pid, 0)
    return child_exit_status


def _capture_output(input_fileno, output_fileno, master_fd, buffer_size=1024):
    """Send data from input_fileno to master_fd and send data from master_fd to
    output_fileno and to the caller

    The implementation of this method is mostly copied from the pty.spawn
    function of the CPython standard library. It has been modified in order to
    make the `record` function a generator.

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
    """Merge event records together if they are close enough

    The time elapsed between two consecutive event records returned by this
    function is guaranteed to be at least min_rec_duration.

    The duration of each record is also computed. Any record with a duration
    greater than `max_rec_duration` will see its duration reduce to this value.
    The duration of the last record can't be computed and is simply set to
    `last_rec_duration`.

    :param event_records: Sequence of records in asciicast v2 format
    :param min_rec_duration: Minimum time between two records returned by the
    function in milliseconds.
    :param max_rec_duration: Maximum duration of a record in milliseconds
    :param last_rec_duration: Duration of the last record in milliseconds
    :return: Sequence of records with duration
    """
    # TODO: itertools.accumulate?
    current_string = ''
    current_time = 0
    dropped_time = 0

    if max_rec_duration:
        max_rec_duration /= 1000

    for event_record in event_records:
        assert isinstance(event_record, AsciiCastV2Event)
        # Silently ignoring the duration on input records is a source
        # of confusion so fail hard if the duration is set
        assert event_record.duration is None
        if event_record.event_type != 'o':
            continue

        time_between_events = event_record.time - (current_time + dropped_time)
        if time_between_events * 1000 >= min_rec_duration:
            if max_rec_duration:
                if max_rec_duration < time_between_events:
                    dropped_time += time_between_events - max_rec_duration
                    time_between_events = max_rec_duration
            accumulator_event = AsciiCastV2Event(time=current_time,
                                                 event_type='o',
                                                 event_data=current_string,
                                                 duration=time_between_events)
            yield accumulator_event
            current_string = ''
            current_time += time_between_events

        current_string += event_record.event_data

    accumulator_event = AsciiCastV2Event(time=current_time,
                                         event_type='o',
                                         event_data=current_string,
                                         duration=last_rec_duration / 1000)
    yield accumulator_event


Configuration = namedtuple('Configuration', ['width', 'height'])
DisplayLine = namedtuple('DisplayLine', ['row', 'line', 'time', 'duration'])
DisplayLine.__new__.__defaults__ = (None,)


def record(process_args, columns, lines, input_fileno, output_fileno):
    """Record a process in asciicast v2 format

    The records returned by this method are:
        - a single header containing configuration information
        - multiple event records made of data captured from the terminal and
        timing information (except for record duration which needs to be
        computed separately)

    :param process_args: Arguments required to spawn the process (list of
    string)
    :param columns: Width of the terminal screen (integer)
    :param lines: Height of the terminal screen (integer)
    :param input_fileno: File descriptor that will be used as the standard
    input of the process
    :param output_fileno: File descriptor that will be used as the standard
    output of the process

    When using `sys.stdout.fileno()` for `output_fileno` there is a risk
    that the terminal is left in an unusable state if `record` fails. To
    prevent this, `record` should be called inside the `TerminalMode`
    context manager.
    """
    yield AsciiCastV2Header(version=2, width=columns, height=lines, theme=None)

    # TODO: why start != 0?
    start = None
    utf8_decoder = codecs.getincrementaldecoder('utf-8')('replace')
    for data, time in _record(process_args, columns, lines, input_fileno, output_fileno):
        if start is None:
            start = time

        yield AsciiCastV2Event(time=(time - start).total_seconds(),
                               event_type='o',
                               event_data=utf8_decoder.decode(data),
                               duration=None)


def screen_events(records, min_frame_dur=1, max_frame_dur=None, last_frame_dur=1000):
    """Yields events describing updates to the screen for this recording

    The first event yielded is an instance of Configuration which
    describes the geometry of the screen.
    All following events are instances of DisplayLine. Those
    events describe the appearance of a line on the screen (if the duration
    of the event is set to None) or the erasure of a line (if the duration
    of the event is an integer).

    Before updates to the screen are reported to the caller they will be
    coalesced so that the mininum duration between two updates is at least
    `min_frame_dur` milliseconds. Events with a duration greater than
    `max_frame_dur` will see their duration reduced to that value.

    The duration of all events lasting until the end of the animation
    will be adjusted so that the last frame of the animation lasts
    `last_frame_dur`

    :param records: Terminal session record in Asciicast v2 format
    :param min_frame_dur: Minimum frame duration in milliseconds (integer)
    :param min_frame_dur: Minimum frame duration in milliseconds (integer)
    :param max_frame_dur: Maximum frame duration in milliseconds (None or
    integer)
    :param last_frame_dur: Duration of the last frame of the animation
    (integer)
    """
    if not isinstance(records, Iterator):
        records = iter(records)

    header = next(records)
    assert isinstance(header, AsciiCastV2Header)

    if not max_frame_dur and header.idle_time_limit:
        max_frame_dur = int(header.idle_time_limit * 1000)
    yield Configuration(header.width, header.height)

    screen = pyte.Screen(header.width, header.height)
    stream = pyte.Stream(screen)

    timed_records = _group_by_time(records, min_frame_dur, max_frame_dur,
                                   last_frame_dur)
    last_cursor = None
    display_events = {}
    time = 0
    for record_ in timed_records:
        assert isinstance(record_, AsciiCastV2Event)
        for char in record_.event_data:
            stream.feed(char)
        redraw_buffer, last_cursor = _redraw_buffer(screen, last_cursor)
        display_events, events = _feed(redraw_buffer, display_events, time)
        if events:
            yield events
        screen.dirty.clear()
        time += int(1000 * record_.duration)

    events = []
    for row in list(display_events):
        event_without_duration = display_events.pop(row)
        duration = time - event_without_duration.time
        events.append(event_without_duration._replace(duration=duration))

    if events:
        yield events


def _redraw_buffer(screen, last_cursor):
    """Return lines of the screen to be redrawn and the current cursor

    Most of the work is done by Pyte through Screen.dirty. We just
    need to monitor updates to the cursor.
    """
    assert isinstance(screen, pyte.Screen)
    assert isinstance(last_cursor, (type(None), pyte.screens.Cursor))

    rows_changed = set(screen.dirty)
    if screen.cursor != last_cursor:
        if not screen.cursor.hidden:
            rows_changed.add(screen.cursor.y)
        if last_cursor is not None and not last_cursor.hidden:
            rows_changed.add(last_cursor.y)

    buffer = defaultdict(dict)
    for row in rows_changed:
        buffer[row] = {
            column: anim.CharacterCell.from_pyte(screen.buffer[row][column])
            for column in screen.buffer[row]
        }

    if screen.cursor != last_cursor and not screen.cursor.hidden:
        row, column = screen.cursor.y, screen.cursor.x
        try:
            data = screen.buffer[row][column].data
        except KeyError:
            data = ' '

        cursor_char = pyte.screens.Char(data=data,
                                        fg=screen.cursor.attrs.fg,
                                        bg=screen.cursor.attrs.bg,
                                        reverse=True)
        buffer[row][column] = anim.CharacterCell.from_pyte(cursor_char)

    current_cursor = copy(screen.cursor)
    return buffer, current_cursor


def _feed(redraw_buffer, display_events, time):
    """Return events based on the lines to redraw and the lines on screen

    Warning: display_events is updated in place (and also returned)
    """
    events = []

    # Send TerminalDisplayDuration event for old lines that were
    # displayed on the screen and need to be redrawn
    for row in list(display_events):
        if row in redraw_buffer:
            event_without_duration = display_events.pop(row)
            duration = time - event_without_duration.time
            events.append(event_without_duration._replace(duration=duration))

    # Send TerminalDisplayLine event for non empty new (or updated) lines
    for row in redraw_buffer:
        if redraw_buffer[row]:
            display_events[row] = DisplayLine(row, redraw_buffer[row], time,
                                              None)
            events.append(display_events[row])

    return display_events, events


def get_terminal_size(fileno):
    try:
        columns, lines = os.get_terminal_size(fileno)
    except OSError:
        columns, lines = 80, 24

    return columns, lines

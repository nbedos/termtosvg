"""UNIX terminal recording functionalities

This module exposes functions for
    - recording the output of a shell process in asciicast v2 format (`record`)
    - producing frames (2D array of CharacterCell) from the raw output of
    `record` (`timed_frames`)

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
from collections import defaultdict, namedtuple
from typing import Iterator

import pyte
import pyte.screens

from termtosvg import anim
from termtosvg.asciicast import AsciiCastV2Event, AsciiCastV2Header

TimedFrame = namedtuple('TimedFrame', ['time', 'duration', 'buffer'])


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


def timed_frames(records, min_frame_dur=1, max_frame_dur=None, last_frame_dur=1000):
    """Return a tuple made of the geometry of the screen and a generator of
    instances of TimedFrame computed from asciicast records

    Asciicast records are first coalesced so that the mininum duration between
    two frames is at least `min_frame_dur` milliseconds. Events with a duration
    greater than `max_frame_dur` will see their duration reduced to that value.

    The duration of all frames lasting until the end of the animation
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

    def generator():
        screen = pyte.Screen(header.width, header.height)
        stream = pyte.Stream(screen)
        timed_records = _group_by_time(records, min_frame_dur, max_frame_dur,
                                       last_frame_dur)

        for record_ in timed_records:
            assert isinstance(record_, AsciiCastV2Event)
            for char in record_.event_data:
                stream.feed(char)
            yield TimedFrame(int(1000 * record_.time),
                             int(1000 * record_.duration),
                             _screen_buffer(screen))

    return (header.width, header.height), generator()


def _screen_buffer(screen):
    assert isinstance(screen, pyte.Screen)

    buffer = defaultdict(dict)
    for row in range(screen.lines):
        buffer[row] = {
            column: anim.CharacterCell.from_pyte(screen.buffer[row][column])
            for column in screen.buffer[row]
        }

    if not screen.cursor.hidden:
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
    return buffer


def get_terminal_size(fileno):
    try:
        columns, lines = os.get_terminal_size(fileno)
    except OSError:
        columns, lines = 80, 24

    return columns, lines

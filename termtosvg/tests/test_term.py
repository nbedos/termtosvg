import itertools
import os
import time
import unittest
from unittest.mock import MagicMock, patch

import pyte

import termtosvg.anim as anim
from termtosvg import term
from termtosvg.asciicast import AsciiCastV2Event, AsciiCastV2Header, AsciiCastV2Theme

commands = [
    'echo $SHELL && sleep 0.1;\r\n',
    'date && sleep 0.1;\r\n',
    'uname && sleep 0.1;\r\n',
    'w',
    'h',
    'o',
    'a',
    'm',
    'i\r\n',
    'exit;\r\n'
]


THEME = AsciiCastV2Theme('#000000', '#FFFFFF', ':'.join(['#123456'] * 16))
CURSOR_CHAR = anim.CharacterCell(' ', 'background', 'foreground')

unittest.TestCase.maxDiff = None


class TestTerm(unittest.TestCase):
    def test__record(self):
        fd_in_read, fd_in_write = os.pipe()
        fd_out_read, fd_out_write = os.pipe()

        lines = 24
        columns = 80

        pid = os.fork()
        if pid == 0:
            # Child process
            for line in commands:
                os.write(fd_in_write, line.encode('utf-8'))
                time.sleep(0.060)
            os._exit(0)

        # Parent process
        with term.TerminalMode(fd_in_read):
            for _ in term._record(['sh'], columns, lines, fd_in_read, fd_out_write):
                pass

        os.waitpid(pid, 0)
        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test_record(self):
        # Use pipes in lieu of stdin and stdout
        fd_in_read, fd_in_write = os.pipe()
        fd_out_read, fd_out_write = os.pipe()

        lines = 24
        columns = 80

        pid = os.fork()
        if pid == 0:
            # Child process
            for line in commands:
                os.write(fd_in_write, line.encode('utf-8'))
                time.sleep(0.060)
            os._exit(0)

        # Parent process
        with term.TerminalMode(fd_in_read):
            for _ in term.record(['sh'], columns, lines, fd_in_read, fd_out_write):
                pass

        os.waitpid(pid, 0)
        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test__buffer_simple_events(self):
        escape_sequences = ['{}\r\n'.format(i) for i in range(5)]

        screen = pyte.Screen(80, 24)
        stream = pyte.Stream(screen)
        for count, escape_sequence in enumerate(escape_sequences):
            with self.subTest(case='Simple events (record #{})'.format(count)):
                stream.feed(escape_sequence)
                buffer = term._screen_buffer(screen)
                expected_buffer = {}
                for i in range(screen.lines):
                    if i <= count:
                        expected_buffer[i] = {0: anim.CharacterCell(str(i))}
                    elif i == count+1:
                        expected_buffer[i] = {0: CURSOR_CHAR}
                    else:
                        expected_buffer[i] = {}

                self.assertEqual(expected_buffer, buffer)

    def test__buffer_hidden_cursor(self):
        """Ensure hidden cursor don't appear in the buffer return by _redraw_buffer
        Ensure that only one cursor is present in the buffer"""
        #   '\u001b[?25h' : display cursor
        #   '\u001b[?25l' : hide cursor
        escape_sequences = [
            '\u001b[?25ha',
            '\r\n\u001b[?25lb',
            '\r\n\u001b[?25hc',
        ]

        screen = pyte.Screen(80, 24)
        stream = pyte.Stream(screen)

        expected_cursors = [
            ((1, 0), True),
            ((1, 1), False),
            ((1, 2), True),
        ]
        z = itertools.zip_longest(expected_cursors, escape_sequences)
        for count, ((cursor_pos, cursor_visible), escape_sequence) in enumerate(z):
            with self.subTest(case='Hidden cursor - item #{}'.format(count)):
                stream.feed(escape_sequence)
                buffer = term._screen_buffer(screen)
                column, line = cursor_pos
                if cursor_visible:
                    self.assertEqual(buffer[line][column], CURSOR_CHAR)
                # Ensure old cursors are deleted
                for row in buffer:
                    for column in buffer[row]:
                        if buffer[row][column].text == ' ':
                            self.assertEqual((column, row), cursor_pos)

    def test_timed_frames_simple_events(self):
        records = [AsciiCastV2Header(version=2, width=80, height=24, theme=THEME)] + \
                  [AsciiCastV2Event(time=i,
                                    event_type='o',
                                    event_data='{}\r\n'.format(i),
                                    duration=None)
                   for i in range(0, 2)]
        geometry, frames = term.timed_frames(records, 1, None, 42)

        self.assertEqual(geometry, (80, 24))

        expected_frames = [
            term.TimedFrame(0, 1000, {
                0: {0: anim.CharacterCell('0')},
                1: {0: CURSOR_CHAR},
            }),
            term.TimedFrame(1000, 42, {
                0: {0: anim.CharacterCell('0')},
                1: {0: anim.CharacterCell('1')},
                2: {0: CURSOR_CHAR},
            })
        ]

        z = itertools.zip_longest(expected_frames, frames)
        for (expected_frame, frame) in z:
            self.assertEqual(expected_frame.time, frame.time)
            self.assertEqual(expected_frame.duration, frame.duration)
            for row in frame.buffer:
                if row in expected_frame.buffer:
                    self.assertEqual(expected_frame.buffer[row],
                                     frame.buffer[row])
                else:
                    self.assertEqual({}, frame.buffer[row])

    def test_timed_frames_unprintable_chars(self):
        # Ensure zero width characters in terminal output does not result
        # in Pyte dropping all following data
        # Issue https://github.com/nbedos/termtosvg/issues/89

        # test_text = "e🕵️‍a"
        test_text = (b'e' +
                     b'\xf0\x9f\x95\xb5' +  # sleuth emoji
                     b'\xef\xb8\x8f' +      # variation selector 16
                     b'\xe2\x80\x8d' +      # zero width joiner
                     b'a').decode('utf-8')  # character that should be preserved

        records = [
            AsciiCastV2Header(version=2, width=80, height=24, theme=THEME),
            AsciiCastV2Event(0, 'o', test_text, None),
        ]
        _, events = term.timed_frames(records, 1, None, last_frame_dur=1000)

        frame = next(events)
        characters = ''.join(frame.buffer[0][col].text
                             for col in frame.buffer[0])

        # Ensure data following sleuth emoji wasn't ignored
        # (rstrip() removes blank cursor character at end of line)
        self.assertEqual(characters.rstrip()[-1], test_text[-1])

    def test_get_terminal_size(self):
        with self.subTest(case='Successful get_terminal_size call'):
            term_size_mock = MagicMock(return_value=(42, 84))
            with patch('os.get_terminal_size', term_size_mock):
                cols, lines, = term.get_terminal_size(-1)
                self.assertEqual(cols, 42)
                self.assertEqual(lines, 84)

    def test__group_by_time(self):
        event_records = [
            AsciiCastV2Event(0, 'o', '1', None),
            AsciiCastV2Event(5, 'o', '2', None),
            AsciiCastV2Event(8, 'o', '3', None),
            AsciiCastV2Event(20, 'o', '4', None),
            AsciiCastV2Event(21, 'o', '5', None),
            AsciiCastV2Event(30, 'o', '6', None),
            AsciiCastV2Event(31, 'o', '7', None),
            AsciiCastV2Event(32, 'o', '8', None),
            AsciiCastV2Event(33, 'o', '9', None),
            AsciiCastV2Event(43, 'o', '10', None),
        ]

        with self.subTest(case='maximum record duration'):
            grouped_event_records_max = [
                AsciiCastV2Event(0, 'o', '1', 5),
                AsciiCastV2Event(5, 'o', '23', 6),
                AsciiCastV2Event(11, 'o', '45', 6),
                AsciiCastV2Event(17, 'o', '6789', 6),
                AsciiCastV2Event(23, 'o', '10', 1.234),
            ]
            result = list(term._group_by_time(event_records, 5000, 6000, 1234))
            self.assertEqual(grouped_event_records_max, result)

        with self.subTest(case='no maximum record duration'):
            grouped_event_records_no_max = [
                AsciiCastV2Event(0, 'o', '1', 5),
                AsciiCastV2Event(5, 'o', '23', 15),
                AsciiCastV2Event(20, 'o', '45', 10),
                AsciiCastV2Event(30, 'o', '6789', 13),
                AsciiCastV2Event(43, 'o', '10', 1.234),
            ]
            result = list(term._group_by_time(event_records, 5000, None, 1234))
            self.assertEqual(grouped_event_records_no_max, result)

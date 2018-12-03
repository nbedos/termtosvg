import os
import time
import unittest
from unittest.mock import MagicMock, patch

import termtosvg.anim as anim
from termtosvg import term
from termtosvg.asciicast import AsciiCastV2Header, AsciiCastV2Event, AsciiCastV2Theme

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


class TestTerm(unittest.TestCase):
    def test__record(self):
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

    def test_replay(self):
        theme = AsciiCastV2Theme('#000000', '#FFFFFF', ':'.join(['#123456'] * 16))

        with self.subTest(case='One shell command per event'):
            nbr_records = 5

            records = [AsciiCastV2Header(version=2, width=80, height=24, theme=theme)] + \
                      [AsciiCastV2Event(time=i,
                                        event_type='o',
                                        event_data='{}\r\n'.format(i).encode('utf-8'),
                                        duration=None)
                       for i in range(1, nbr_records)]

            records = term.replay(records, lambda x: x.data, 5000, None, 1000)
            # Last blank line is the cursor
            lines = [str(i) for i in range(nbr_records)] + [' ']
            for i, record in enumerate(records):
                # Skip header and cursor line
                if i != 0:
                    self.assertEqual(record.line[0], lines[i])

        with self.subTest(case='Shell command spread over multiple lines'):
            records = [AsciiCastV2Header(version=2, width=80, height=24, theme=theme)] + \
                      [AsciiCastV2Event(time=i * 60,
                                        event_type='o',
                                        event_data=data.encode('utf-8'),
                                        duration=None)
                       for i, data in enumerate(commands)]

            screen = {}
            for record in term.replay(records, lambda x: x.data, 50, None, 1000):
                if hasattr(record, 'line'):
                    screen[record.row] = ''.join(record.line[i] for i in sorted(record.line))

            cmds = [cmd for cmd in ''.join(commands).split('\r\n') if cmd]
            cursor = [' ']
            expected_screen = dict(enumerate(cmds + cursor))
            self.assertEqual(expected_screen, screen)

        with self.subTest(case='Hidden cursor'):
            # '\u001b[?25h' : display cursor
            # '\u001b[?25l' : hide cursor
            records = [AsciiCastV2Header(version=2, width=80, height=24, theme=theme)] + \
                      [
                          AsciiCastV2Event(0, 'o', '\u001b[?25haaaa'.encode('utf-8'), None),
                          AsciiCastV2Event(100, 'o', '\r\n\u001b[?25lbbbb'.encode('utf-8'), None),
                          AsciiCastV2Event(200, 'o', '\r\n\u001b[?25hcccc'.encode('utf-8'), None),
                      ]

            gen = term.replay(records, anim.CharacterCell.from_pyte, 50, None, 1000)
            header, *events = list(gen)

            # Event #0: First line - cursor displayed after 'aaaa'
            self.assertEqual(events[0].row, 0)
            self.assertEqual(events[0].line[4].color, 'background')
            self.assertEqual(events[0].line[4].background_color, 'foreground')

            # Event #1: First line - cursor removed at position 4
            self.assertEqual(events[1].row, 0)
            self.assertNotIn(4, events[1].line)

            # Event #2: Second line - cursor hidden
            self.assertEqual(events[2].row, 1)
            self.assertNotIn(4, events[2].line)

            # Event #3: Third line - cursor displayed after 'cccc'
            self.assertEqual(events[3].row, 2)
            self.assertEqual(events[3].line[4].color, 'background')
            self.assertEqual(events[3].line[4].background_color, 'foreground')

    def test_get_terminal_size(self):
        with self.subTest(case='Successful get_terminal_size call'):
            term_size_mock = MagicMock(return_value=(42, 84))
            with patch('os.get_terminal_size', term_size_mock):
                cols, lines, = term.get_terminal_size(-1)
                self.assertEqual(cols, 42)
                self.assertEqual(lines, 84)

    def test__group_by_time(self):
        event_records = [
            AsciiCastV2Event(0, 'o', b'1', None),
            AsciiCastV2Event(5, 'o', b'2', None),
            AsciiCastV2Event(8, 'o', b'3', None),
            AsciiCastV2Event(20, 'o', b'4', None),
            AsciiCastV2Event(21, 'o', b'5', None),
            AsciiCastV2Event(30, 'o', b'6', None),
            AsciiCastV2Event(31, 'o', b'7', None),
            AsciiCastV2Event(32, 'o', b'8', None),
            AsciiCastV2Event(33, 'o', b'9', None),
            AsciiCastV2Event(43, 'o', b'10', None),
        ]

        with self.subTest(case='maximum record duration'):
            grouped_event_records_max = [
                AsciiCastV2Event(0, 'o', b'1', 5),
                AsciiCastV2Event(5, 'o', b'23', 6),
                AsciiCastV2Event(11, 'o', b'45', 6),
                AsciiCastV2Event(17, 'o', b'6789', 6),
                AsciiCastV2Event(23, 'o', b'10', 1.234),
            ]
            result = list(term._group_by_time(event_records, 5000, 6000, 1234))
            self.assertEqual(grouped_event_records_max, result)

        with self.subTest(case='no maximum record duration'):
            grouped_event_records_no_max = [
                AsciiCastV2Event(0, 'o', b'1', 5),
                AsciiCastV2Event(5, 'o', b'23', 15),
                AsciiCastV2Event(20, 'o', b'45', 10),
                AsciiCastV2Event(30, 'o', b'6789', 13),
                AsciiCastV2Event(43, 'o', b'10', 1.234),
            ]
            result = list(term._group_by_time(event_records, 5000, None, 1234))
            self.assertEqual(grouped_event_records_no_max, result)

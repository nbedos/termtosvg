import os
import time
import unittest
from unittest.mock import MagicMock, patch

from termtosvg import term
from termtosvg.asciicast import AsciiCastHeader, AsciiCastEvent, AsciiCastTheme

xresources_valid = """*background:	#002b36
*foreground:	#839496
*color0:	#073642
*color1:	#dc322f
*color2:	#859900
*color3:	#b58900
*color4:	#268bd2
*color5:	#d33682
*color6:	#2aa198
termtosvg.color7:	#eee8d5
*color9:	#cb4b16
*color8:	#002b36
*color10:	#586e75
*color11:	#657b83
*color12:	#839496
termtosvg.color13:	#6c71c4
*color14:	#93a1a1
termtosvg.color15:	#fdf6e3"""

xresources_minimal = """*background:	#002b36
*foreground:	#839496
*color0:	#073642
*color1:	#dc322f
*color2:	#859900
*color3:	#b58900
*color4:	#268bd2
*color5:	#d33682
*color6:	#2aa198
termtosvg.color7:	#eee8d5
"""

xresources_incomplete = """*background:	#002b36
*foreground:	#839496
*color1:	#dc322f"""

xresources_empty = ''

commands = [
    'echo $SHELL && sleep 0.1;\r\n',
    'tree && 0.1;\r\n',
    'ls && sleep 0.1;\r\n',
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
            for _ in term._record(columns, lines, fd_in_read, fd_out_write):
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
        theme = AsciiCastTheme('#000000', '#111111', ':'.join(['#123456']*8))

        pid = os.fork()
        if pid == 0:
            # Child process
            for line in commands:
                os.write(fd_in_write, line.encode('utf-8'))
                time.sleep(0.060)
            os._exit(0)

        # Parent process
        with term.TerminalMode(fd_in_read):
            for _ in term.record(columns, lines, theme, fd_in_read, fd_out_write):
                pass

        os.waitpid(pid, 0)
        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test_replay(self):
        def pyte_to_str(x, _):
            return x.data

        fallback_theme = AsciiCastTheme('#000000', '#000000', ':'.join(['#000000'] * 16))
        theme = AsciiCastTheme('#000000', '#FFFFFF', ':'.join(['#123456'] * 16))

        with self.subTest(case='One shell command per event'):
            nbr_records = 5

            records = [AsciiCastHeader(version=2, width=80, height=24, theme=theme)] + \
                      [AsciiCastEvent(time=i,
                                      event_type='o',
                                      event_data='{}\r\n'.format(i).encode('utf-8'),
                                      duration=None)
                       for i in range(1, nbr_records)]

            records = term.replay(records, pyte_to_str, fallback_theme, 50, 1000)
            # Last blank line is the cursor
            lines = [str(i) for i in range(nbr_records)] + [' ']
            for i, record in enumerate(records):
                # Skip header and cursor line
                if i == 0:
                    pass
                else:
                    self.assertEqual(record.line[0], lines[i])

        with self.subTest(case='Shell command spread over multiple lines, no theme'):
            records = [AsciiCastHeader(version=2, width=80, height=24, theme=None)] + \
                      [AsciiCastEvent(time=i * 60,
                                      event_type='o',
                                      event_data=data.encode('utf-8'),
                                      duration=None)
                       for i, data in enumerate(commands)]

            screen = {}
            for record in term.replay(records, pyte_to_str, theme, 50, 1000):
                if hasattr(record, 'line'):
                    screen[record.row] = ''.join(record.line[i] for i in sorted(record.line))

            cmds = [cmd for cmd in ''.join(commands).split('\r\n') if cmd]
            cursor = [' ']
            expected_screen = dict(enumerate(cmds + cursor))
            self.assertEqual(expected_screen, screen)

    def test_default_themes(self):
        term.default_themes()

    def test_get_configuration(self):
        _get_x_mock = MagicMock(return_value=xresources_valid)
        with patch('termtosvg.term._get_xresources', _get_x_mock):
            with self.subTest(case='Failing get_terminal_size call'):
                # Pass an invalid fileno (-1) to get_configuration.
                # The call should still work and return the default terminal geometry
                cols, lines, theme = term.get_configuration(-1)
                self.assertEqual(cols, 80)
                self.assertEqual(lines, 24)
                self.assertIsNotNone(theme)

            with self.subTest(case='Successful get_terminal_size call'):
                term_size_mock = MagicMock(return_value=(42, 84))
                with patch('os.get_terminal_size', term_size_mock):
                    cols, lines, theme = term.get_configuration(-1)
                    self.assertEqual(cols, 42)
                    self.assertEqual(lines, 84)
                    self.assertIsNotNone(theme)

        _get_x_mock = MagicMock(side_effect=term.DisplayError(None))
        with patch('termtosvg.term._get_xresources', _get_x_mock):
            with self.subTest(case='Failing _get_xresources call'):
                term_size_mock = MagicMock(return_value=(42, 84))
                with patch('os.get_terminal_size', term_size_mock):
                    cols, lines, theme = term.get_configuration(-1)
                    self.assertEqual(cols, 42)
                    self.assertEqual(lines, 84)
                    self.assertIsNone(theme)

        _get_x_mock = MagicMock(return_value=xresources_incomplete)
        with patch('termtosvg.term._get_xresources', _get_x_mock):
            with self.subTest(case='Invalid Xresources string'):
                term_size_mock = MagicMock(return_value=(42, 84))
                with patch('os.get_terminal_size', term_size_mock):
                    cols, lines, theme = term.get_configuration(-1)
                    self.assertEqual(cols, 42)
                    self.assertEqual(lines, 84)
                    self.assertIsNone(theme)

    def test__group_by_time(self):
        event_records = [
            AsciiCastEvent(0, 'o', b'1', None),
            AsciiCastEvent(50, 'o', b'2', None),
            AsciiCastEvent(80, 'o', b'3', None),
            AsciiCastEvent(200, 'o', b'4', None),
            AsciiCastEvent(210, 'o', b'5', None),
            AsciiCastEvent(300, 'o', b'6', None),
            AsciiCastEvent(310, 'o', b'7', None),
            AsciiCastEvent(320, 'o', b'8', None),
            AsciiCastEvent(330, 'o', b'9', None)
        ]

        grouped_event_records = [
            AsciiCastEvent(0, 'o', b'1', 50),
            AsciiCastEvent(50, 'o', b'23', 150),
            AsciiCastEvent(200, 'o', b'45', 100),
            AsciiCastEvent(300, 'o', b'6789', 1234)
        ]

        result = list(term._group_by_time(event_records, 50, 1234))
        self.assertEqual(grouped_event_records, result)

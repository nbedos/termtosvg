import os
import time
import unittest
from unittest.mock import MagicMock, patch

from vectty import term

xresources_valid = """*background:	#002b36
*foreground:	#839496
*color0:	#073642
*color1:	#dc322f
*color2:	#859900
*color3:	#b58900
*color4:	#268bd2
*color5:	#d33682
*color6:	#2aa198
Svg.color7:	#eee8d5
*color9:	#cb4b16
*color8:	#002b36
*color10:	#586e75
*color11:	#657b83
*color12:	#839496
Svg.color13:	#6c71c4
*color14:	#93a1a1
Svg.color15:	#fdf6e3"""

xresources_minimal = """*background:	#002b36
*foreground:	#839496
*color0:	#073642
*color1:	#dc322f
*color2:	#859900
*color3:	#b58900
*color4:	#268bd2
*color5:	#d33682
*color6:	#2aa198
Svg.color7:	#eee8d5
"""

xresources_incomplete = """*background:	#002b36
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

        # Parent process
        for _ in term._record(columns, lines, fd_in_read, fd_out_write):
            pass

        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test_record(self):
        # Use pipes in lieu of stdin and stdout
        fd_in_read, fd_in_write = os.pipe()
        fd_out_read, fd_out_write = os.pipe()

        lines = 24
        columns = 80
        theme = term.AsciiCastTheme('#000000', '#111111', ':'.join(['#123456']*8))

        pid = os.fork()
        if pid == 0:
            # Child process
            for line in commands:
                os.write(fd_in_write, line.encode('utf-8'))
                time.sleep(0.060)

        # Parent process
        for _ in term.record(columns, lines, theme, fd_in_read, fd_out_write):
            pass

        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test_replay(self):
        def pyte_to_str(x):
            return x.data

        with self.subTest(case='One shell command per event'):
            nbr_records = 5
            records = [term.AsciiCastHeader(version=2, width=80, height=24, theme=None)] + \
                      [term.AsciiCastEvent(time=i,
                                           event_type='o',
                                           event_data=f'{i}\r\n'.encode('utf-8'),
                                           duration=None)
                       for i in range(1, nbr_records)]

            records = term.replay(records, pyte_to_str, 50, 1000)
            for i, record in enumerate(records):
                if i == 0:
                    pass
                else:
                    self.assertEqual(record.line[0], str(i))

        with self.subTest(case='Shell command spread over multiple lines'):
            records = [term.AsciiCastHeader(version=2, width=80, height=24, theme=None)] + \
                      [term.AsciiCastEvent(time=i*60,
                                           event_type='o',
                                           event_data=data.encode('utf-8'),
                                           duration=None)
                       for i, data in enumerate(commands)]

            screen = {}
            for record in term.replay(records, pyte_to_str, 50, 1000):
                if hasattr(record, 'line'):
                    screen[record.row] = ''.join(record.line[i] for i in sorted(record.line))

            expected_screen = dict(enumerate(cmd for cmd in ''.join(commands).split('\r\n') if cmd))
            self.assertEqual(expected_screen, screen)

    def test__parse_xresources(self):
        with self.subTest(case='All valid colors'):
            theme = term._parse_xresources(xresources_valid)
            colors = theme.palette.split(':')
            self.assertTrue(len(colors), 16)
            self.assertEqual(colors[0], '#073642')
            self.assertEqual(colors[15], '#fdf6e3')
            self.assertEqual(theme.bg, '#002b36')
            self.assertEqual(theme.fg, '#839496')

        with self.subTest(case='Minimal Xresources'):
            theme = term._parse_xresources(xresources_minimal)
            colors = theme.palette.split(':')
            self.assertTrue(len(colors), 8)
            self.assertEqual(colors[0], '#073642')
            self.assertEqual(colors[7], '#eee8d5')
            self.assertEqual(theme.bg, '#002b36')
            self.assertEqual(theme.fg, '#839496')

        with self.subTest(case='Not all colors defined'):
            with self.assertRaises(KeyError):
                term._parse_xresources(xresources_incomplete)

        with self.subTest(case='Empty Xresource'):
            with self.assertRaises(KeyError):
                term._parse_xresources(xresources_empty)

    def test_get_configuration(self):
        m = MagicMock()
        m.screen().root.get_full_property.return_value.value = xresources_valid.encode('utf-8')
        Display_mock = MagicMock(return_value=m)
        with patch('Xlib.display.Display', Display_mock):
            with self.subTest(case='Failing get_terminal_size call'):
                term.get_configuration(-1)

            with self.subTest(case='Successful get_terminal_size call'):
                term_size_mock = MagicMock(return_value=(42, 84))
                with patch('os.get_terminal_size', term_size_mock):
                    term.get_configuration(-1)

    def test__group_by_time(self):
        event_records = [
            term.AsciiCastEvent(0, 'o', b'1', None),
            term.AsciiCastEvent(50, 'o', b'2', None),
            term.AsciiCastEvent(80, 'o', b'3', None),
            term.AsciiCastEvent(200, 'o', b'4', None),
            term.AsciiCastEvent(210, 'o', b'5', None),
            term.AsciiCastEvent(300, 'o', b'6', None),
            term.AsciiCastEvent(310, 'o', b'7', None),
            term.AsciiCastEvent(320, 'o', b'8', None),
            term.AsciiCastEvent(330, 'o', b'9', None)
        ]

        grouped_event_records = [
            term.AsciiCastEvent(0, 'o', b'1', 50),
            term.AsciiCastEvent(50, 'o', b'23', 150),
            term.AsciiCastEvent(200, 'o', b'45', 100),
            term.AsciiCastEvent(300, 'o', b'6789', 1234)
        ]

        result = list(term._group_by_time(event_records, 50, 1234))
        self.assertEqual(grouped_event_records, result)

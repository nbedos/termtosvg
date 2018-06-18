import unittest

from termtosvg.asciicast import AsciiCastHeader, AsciiCastEvent, AsciiCastRecord, AsciiCastTheme
import termtosvg.term as term
from tests.test_term import xresources_valid, xresources_empty, xresources_incomplete, \
    xresources_minimal


class TestAsciicast(unittest.TestCase):
    def test_AsciiCastHeader(self):
        with self.subTest(case='invalid time'):
            with self.assertRaises(TypeError):
                AsciiCastHeader.from_json_line("""{"version": "x", "width": 212, "height": 53}""")

        with self.subTest(case='invalid width'):
            with self.assertRaises(TypeError):
                AsciiCastHeader.from_json_line("""{"version": 2, "width": "x", "height": 53}""")

    def test_AsciiCastEvent(self):
        with self.subTest(case='invalid time'):
            with self.assertRaises(TypeError):
                AsciiCastEvent.from_json_line("""["x", "o", "ls"]""")

        with self.subTest(case='invalid event type'):
            with self.assertRaises(TypeError):
                AsciiCastEvent.from_json_line("""[2.0, 123, "ls"]""")

    cast_lines = [
        # Header: Missing theme
        """{"version": 2, "width": 212, "height": 53}""",
        # Header: 8 color theme
        """{"version": 2, "width": 212, "height": 53, "theme": {"fg": "#000000", "bg": "#AAAAAA", "palette": "#000000:#111111:#222222:#333333:#444444:#555555:#666666:#777777"}}""",
        # Header: 16 color theme
        """{"version": 2, "width": 212, "height": 53, "theme": {"fg": "#000000", "bg": "#AAAAAA", "palette": "#000000:#111111:#222222:#333333:#444444:#555555:#666666:#777777:#888888:#999999:#AAAAAA:#bbbbbb:#CCCCCC:#DDDDDD:#EEEEEE:#ffffff"}}""",
        # Header: additional values
        """{"version": 2, "width": 212, "height": 53, "timestamp": 123456798123}""",
        # Event: Non printable characters
        """[0.010303, "o", "\\u001b[1;31mnico \\u001b[0;34m~\\u001b[0m"]""",
        # Event: Unicode characters
        """[1.146397, "o", "❤ ☀ ☆ ☂ ☻ ♞ ☯ ☭ ☢ € →"]""",
        # Event: time is an integer and not a float
        """[2, "o", "\\r\\n"]""",
    ]

    color_theme_8 = AsciiCastTheme(fg='#000000', bg='#AAAAAA', palette='#000000:#111111:'
                                   '#222222:#333333:#444444:#555555:#666666:#777777')
    color_theme_16 = AsciiCastTheme(fg='#000000', bg='#AAAAAA', palette='#000000:#111111:'
                                    '#222222:#333333:#444444:#555555:#666666:#777777:#888888:'
                                    '#999999:#AAAAAA:#bbbbbb:#CCCCCC:#DDDDDD:#EEEEEE:#ffffff')
    cast_events = [
        AsciiCastHeader(2, 212, 53, None),
        AsciiCastHeader(2, 212, 53, color_theme_8),
        AsciiCastHeader(2, 212, 53, color_theme_16),
        AsciiCastHeader(2, 212, 53, None),
        AsciiCastEvent(0.010303, 'o', '\u001b[1;31mnico \u001b[0;34m~\u001b[0m'.encode('utf-8'), None),
        AsciiCastEvent(1.146397, 'o', '❤ ☀ ☆ ☂ ☻ ♞ ☯ ☭ ☢ € →'.encode('utf-8'), None),
        AsciiCastEvent(2, 'o', b'\r\n', None),
    ]

    def test_from_json(self):
        test_cases = zip(TestAsciicast.cast_lines, TestAsciicast.cast_events)
        for index, (line, event) in enumerate(test_cases):
            with self.subTest(case='line #{}'.format(index)):
                self.assertEqual(event, AsciiCastRecord.from_json_line(line))

    def test_to_json(self):
        test_cases = zip(TestAsciicast.cast_lines, TestAsciicast.cast_events)
        for index, (line, event) in enumerate(test_cases):
            # extra value test case only useful for from_json
            if 'timestamp' in line:
                continue
            with self.subTest(case='line #{}'.format(index)):
                self.assertEqual(event.to_json_line(), line)

    def test_from_xresources(self):
        with self.subTest(case='All valid colors'):
            theme = AsciiCastTheme.from_xresources(xresources_valid)
            colors = theme.palette.split(':')
            self.assertTrue(len(colors), 16)
            self.assertEqual(colors[0], '#073642')
            self.assertEqual(colors[15], '#fdf6e3')
            self.assertEqual(theme.bg, '#002b36')
            self.assertEqual(theme.fg, '#839496')

        with self.subTest(case='Minimal Xresources'):
            theme = AsciiCastTheme.from_xresources(xresources_minimal)
            colors = theme.palette.split(':')
            self.assertTrue(len(colors), 8)
            self.assertEqual(colors[0], '#073642')
            self.assertEqual(colors[7], '#eee8d5')
            self.assertEqual(theme.bg, '#002b36')
            self.assertEqual(theme.fg, '#839496')

        with self.subTest(case='Not all colors defined'):
            with self.assertRaises(ValueError):
                AsciiCastTheme.from_xresources(xresources_incomplete)

        with self.subTest(case='Empty Xresource'):
            with self.assertRaises(ValueError):
                AsciiCastTheme.from_xresources(xresources_empty)

        for theme, xresource_str in term.default_themes().items():
            with self.subTest(case=theme):
                AsciiCastTheme.from_xresources(xresource_str)

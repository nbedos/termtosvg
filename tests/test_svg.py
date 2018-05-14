from collections import defaultdict
import datetime
import os
import pyte.screens
import unittest

from src import svg

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

xresources_incomplete = """*background:	#002b36
*color1:	#dc322f"""

xresources_empty = ''


class TestTerminalSession(unittest.TestCase):
    def test_record(self):
        commands = ['echo $SHELL && sleep 0.1;',
                    'tree && 0.1;',
                    'ls && sleep 0.1;',
                    'whoami && sleep 0.1;',
                    'exit;',
                    '']

        # Use pipes in lieu of stdin and stdout
        fd_in_read, fd_in_write = os.pipe()
        fd_out_read, fd_out_write = os.pipe()

        session = svg.TerminalSession()

        os.write(fd_in_write, '\r\n'.join(commands).encode('utf-8'))
        for item in session.record(input_fileno=fd_in_read, output_fileno=fd_out_write):
            pass

        for fd in [fd_in_read, fd_in_write, fd_out_read, fd_out_write]:
            os.close(fd)

    def test__parse_xresources(self):
        with self.subTest(case='All valid colors'):
            color_mapping = svg.TerminalSession._parse_xresources(xresources_valid)
            for i in range(16):
                self.assertIn(f'color{i}', color_mapping)
            self.assertEqual(color_mapping['background'], '#002b36')
            self.assertEqual(color_mapping['foreground'], '#839496')

        # Should succeed even though colors are missing
        with self.subTest(case='Not all colors defined'):
            svg.TerminalSession._parse_xresources(xresources_incomplete)

        with self.subTest(case='Empty Xresource'):
            svg.TerminalSession._parse_xresources(xresources_empty)

    def test__get_xresources(self):
        svg.TerminalSession._get_xresources()

    def test_get_configuration(self):
        session = svg.TerminalSession()
        session.get_configuration()

    def test__group_by_time(self):
        timings = [(b' ', 0), (b'$', 0), (b' ', 0), (b'c', 60), (b'm', 120), (b'd', 180),
                   (b'\r', 260), (b'\n', 260), (b' ', 260), (b'$', 260), (b' ', 260)]

        now = datetime.datetime.now()
        real_timings = [(bs, now + datetime.timedelta(milliseconds=n)) for bs, n in timings]
        result = svg.TerminalSession._group_by_time(real_timings, threshold=50)

        expected_result = [(b' $ ', now),
                           (b'c', now + datetime.timedelta(milliseconds=60)),
                           (b'm', now + datetime.timedelta(milliseconds=120)),
                           (b'd', now + datetime.timedelta(milliseconds=180)),
                           (b'\r\n $ ', now + datetime.timedelta(milliseconds=260))]
        self.assertEqual(expected_result, list(result))


class TestSVG(unittest.TestCase):
    def test_render_animation(self):
        pass

    def test__render_line_bg_colors(self):
        screen_line = {
            0: pyte.screens.Char('A', bg='red', reverse=False),
            1: pyte.screens.Char('A', bg='red', reverse=False),
            3: pyte.screens.Char('A', bg='red', reverse=False),
            4: pyte.screens.Char('A', bg='blue', reverse=False),
            6: pyte.screens.Char('A', bg='blue', reverse=False),
            7: pyte.screens.Char('A', fg='blue', reverse=True),
            8: pyte.screens.Char('A', bg='green', reverse=False),
            9: pyte.screens.Char('A', bg='red', reverse=False),
            10: pyte.screens.Char('A', bg='red', reverse=False)
        }

        animation = svg.AsciiAnimation()
        rectangles = animation._render_line_bg_colors(screen_line, height=0, line_height=1)
        rect_0, rect_3, rect_4, rect_6, rect_8, rect_9 = sorted(rectangles,
                                                                key=lambda r: r.attribs['x'])

        self.assertEqual(rect_0.attribs['x'], '0ex')
        self.assertEqual(rect_0.attribs['width'], '2ex')
        self.assertEqual(rect_0.attribs['class'], 'red')
        self.assertEqual(rect_3.attribs['x'], '3ex')
        self.assertEqual(rect_4.attribs['x'], '4ex')
        self.assertEqual(rect_6.attribs['x'], '6ex')
        self.assertEqual(rect_6.attribs['class'], 'blue')
        self.assertEqual(rect_8.attribs['x'], '8ex')
        self.assertEqual(rect_8.attribs['class'], 'green')
        self.assertEqual(rect_9.attribs['x'], '9ex')

    def test__render_frame_bg_colors(self):
        buffer = defaultdict(dict)
        buffer_size = 4

        animation = svg.AsciiAnimation()
        with self.subTest(case='Single color buffer'):
            for i in range(buffer_size):
                for j in range(buffer_size):
                    buffer[i][j] = pyte.screens.Char(' ', bg='black')
            animation._render_frame_bg_colors(buffer, 1)

    def test__render_characters(self):
        animation = svg.AsciiAnimation()

        screen_buffer = [
            ((0, 0), pyte.screens.Char('A', fg='red', reverse=False)),
            ((0, 1), pyte.screens.Char('B', fg='blue', reverse=False)),
            ((1, 4), pyte.screens.Char('C', fg='blue', reverse=False)),
            ((1, 6), pyte.screens.Char('D', fg='green', reverse=False)),
            ((2, 8), pyte.screens.Char('E', bg='green', reverse=True)),
            ((2, 9), pyte.screens.Char('F', fg='green', reverse=False, bold=True)),
            ((3, 10), pyte.screens.Char('G', bg='green', reverse=True, bold=True)),
            ((4, 0), pyte.screens.Char(' ', bg='red', reverse=False))
        ]
        all_texts = animation._render_characters(screen_buffer, lambda x: x)
        sorted_texts = sorted((text.text, text) for text in all_texts)
        text_a, text_bc, text_de, text_fg, text_space = [text for _, text in sorted_texts]

        self.assertEqual(text_a.text, 'A')
        self.assertEqual(text_a.attribs['class'], 'red')
        self.assertEqual(text_a.attribs['x'], '0ex')
        self.assertEqual(text_a.attribs['y'], '0.00em')
        self.assertEqual(text_bc.text, 'BC')
        self.assertEqual(text_bc.attribs['class'], 'blue')
        self.assertEqual(text_bc.attribs['x'], '1ex 4ex')
        self.assertEqual(text_bc.attribs['y'], '0.00em 1.00em')
        self.assertEqual(text_de.text, 'DE')
        self.assertEqual(text_de.attribs['class'], 'green')
        self.assertEqual(text_de.attribs['x'], '6ex 8ex')
        self.assertEqual(text_de.attribs['y'], '1.00em 2.00em')
        self.assertEqual(text_fg.text, 'FG')
        self.assertEqual(text_fg.attribs['class'], 'green bold')
        self.assertEqual(text_fg.attribs['x'], '9ex 10ex')
        self.assertEqual(text_fg.attribs['y'], '2.00em 3.00em')

    def test__render_frame_fg(self):
        pass

    def _test_serialize_css_dict(self):
        css = {
            'text': {
                'font-family': 'Dejavu Sans Mono',
                'font-style': 'normal',
                'font-size': '14px',
                'fill':  '#839496'
            },
            '.red': {
                'fill': '#dc322f'
            }
        }
        svg.AsciiAnimation._serialize_css_dict(css)

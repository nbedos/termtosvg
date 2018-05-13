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

    # TODO: Worth testing?
    def test__get_xresources(self):
        svg.TerminalSession._get_xresources()

    def test_get_configuration(self):
        session = svg.TerminalSession()
        session.get_configuration()


class TestSVG(unittest.TestCase):
    def test_group_by_time(self):
        timings = [(b' ', 0), (b'$', 0), (b' ', 0), (b'c', 60), (b'm', 120), (b'd', 180),
                   (b'\r', 260), (b'\n', 260), (b' ', 260), (b'$', 260), (b' ', 260)]

        now = datetime.datetime.now()
        threshold = datetime.timedelta(milliseconds=50)
        real_timings = [(bs, now + datetime.timedelta(milliseconds=n)) for bs, n in timings]
        result = svg.group_by_time(real_timings, threshold=threshold)

        expected_result = [(b' $ ', now),
                           (b'c', now + datetime.timedelta(milliseconds=60)),
                           (b'm', now + datetime.timedelta(milliseconds=120)),
                           (b'd', now + datetime.timedelta(milliseconds=180)),
                           (b'\r\n $ ', now + datetime.timedelta(milliseconds=260))]
        self.assertEqual(expected_result, result)

    def test_render_animation(self):
        pass

    def test_draw_bg(self):
        def mock_char(bg):
            return pyte.screens.Char(' ', bg=bg, reverse=False)

        buffer = defaultdict(dict)
        buffer_size = 4

        with self.subTest(case='Single color buffer'):
            for i in range(buffer_size):
                for j in range(buffer_size):
                    buffer[i][j] = mock_char('black')
            svg.draw_bg(buffer, 10, 'test_bg').tostring()

    def test_serialize_css_dict(self):
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
        print(svg.serialize_css_dict(css))

    def test_draw_fg(self):
        pass

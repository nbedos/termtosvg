from collections import defaultdict
import copy
import datetime
import os
import unittest

from src import vectty

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

        session = vectty.TerminalSession()

        os.write(fd_in_write, '\r\n'.join(commands).encode('utf-8'))
        for item in session.record(input_fileno=fd_in_read, output_fileno=fd_out_write):
            pass

        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test_replay(self):
        def delta_ms(n):
            return datetime.timedelta(milliseconds=n)

        now = datetime.datetime.now()
        bytes = [b'line1\n', b'line2\n', b'line3\n', b'line4\n']
        times = [now + delta_ms(n * 100) for n in range(len(bytes))]

        timings = zip(bytes, times)

        session = vectty.TerminalSession()
        for buffer in session.replay(timings):
            pass

    def test__parse_xresources(self):
        with self.subTest(case='All valid colors'):
            color_mapping = vectty.TerminalSession._parse_xresources(xresources_valid)
            for i in range(16):
                self.assertIn(f'color{i}', color_mapping)
            self.assertEqual(color_mapping['background'], '#002b36')
            self.assertEqual(color_mapping['foreground'], '#839496')

        # Should succeed even though colors are missing
        with self.subTest(case='Not all colors defined'):
            vectty.TerminalSession._parse_xresources(xresources_incomplete)

        with self.subTest(case='Empty Xresource'):
            vectty.TerminalSession._parse_xresources(xresources_empty)

    def test__get_xresources(self):
        vectty.TerminalSession._get_xresources()

    def test_get_configuration(self):
        session = vectty.TerminalSession()
        session.get_configuration()

    def test__group_by_time(self):
        def delta_ms(n):
            return datetime.timedelta(milliseconds=n)
        
        timings = [(b' ', 0), (b'$', 0), (b' ', 0), (b'c', 60), (b'm', 120), (b'd', 180),
                   (b'\r', 260), (b'\n', 260), (b' ', 260), (b'$', 260), (b' ', 260)]

        now = datetime.datetime.now()
        real_timings = [(bs, now + delta_ms(n)) for bs, n in timings]
        result = vectty.TerminalSession._group_by_time(timings=real_timings,
                                                    min_frame_duration=50,
                                                    last_frame_duration=1234)

        expected_result = [(b' $ ', delta_ms(60)),
                           (b'c', delta_ms(60)),
                           (b'm', delta_ms(60)),
                           (b'd', delta_ms(80)),
                           (b'\r\n $ ', delta_ms(1234))]
        self.assertEqual(expected_result, list(result))


class TestSVG(unittest.TestCase):
    def test_render_animation(self):
        pass

    def test__render_line_bg_colors(self):
        screen_line = {
            0: vectty.AsciiChar('A', None, 'red'),
            1: vectty.AsciiChar('A', None, 'red'),
            3: vectty.AsciiChar('A', None, 'red'),
            4: vectty.AsciiChar('A', None, 'blue'),
            6: vectty.AsciiChar('A', None, 'blue'),
            7: vectty.AsciiChar('A', None, 'blue'),
            8: vectty.AsciiChar('A', None, 'green'),
            9: vectty.AsciiChar('A', None, 'red'),
            10: vectty.AsciiChar('A', None, 'red')
        }

        animation = vectty.AsciiAnimation()
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

    # def test__render_frame_bg_colors(self):
    #     buffer = defaultdict(dict)
    #     buffer_size = 4
    #
    #     animation = vectty.AsciiAnimation()
    #     with self.subTest(case='Single color buffer'):
    #         for i in range(buffer_size):
    #             for j in range(buffer_size):
    #                 buffer[i][j] = vectty.AsciiChar(' ')
    #         animation._render_frame_bg_colors(buffer, 1)

    def test__render_characters(self):
        screen_line = {
            0: vectty.AsciiChar('A', 'red', None),
            1: vectty.AsciiChar('B', 'blue', None),
            4: vectty.AsciiChar('C', 'blue', None),
            6: vectty.AsciiChar('D', 'green', None),
            8: vectty.AsciiChar('E', 'green', None),
            9: vectty.AsciiChar('F', 'green', None),
            10: vectty.AsciiChar('G', 'green', None),
            11: vectty.AsciiChar('H', 'red', None),
            20: vectty.AsciiChar(' ', 'ungrouped')
        }
        animation = vectty.AsciiAnimation()
        all_texts = animation._render_characters(screen_line, 1.23)
        sorted_texts = sorted((text.text, text) for text in all_texts)
        text_ah, text_bc, text_defg, text_space = [text for _, text in sorted_texts]

        self.assertEqual(text_ah.text, 'AH')
        self.assertEqual(text_ah.attribs['class'], 'red')
        self.assertEqual(text_ah.attribs['x'], '0ex 11ex')
        self.assertEqual(text_ah.attribs['y'], '1.23em')
        self.assertEqual(text_bc.text, 'BC')
        self.assertEqual(text_bc.attribs['class'], 'blue')
        self.assertEqual(text_bc.attribs['x'], '1ex 4ex')
        self.assertEqual(text_defg.text, 'DEFG')
        self.assertEqual(text_defg.attribs['class'], 'green')
        self.assertEqual(text_defg.attribs['x'], '6ex 8ex 9ex 10ex')

    # def test__render_frame_fg(self):
    #     animation = vectty.AsciiAnimation()
    #
    #     screen_buffer = {
    #         0: {
    #             0: vectty.AsciiChar('A', 'red'),
    #             1: vectty.AsciiChar('B', 'blue'),
    #             4: vectty.AsciiChar('C', 'blue'),
    #             6: vectty.AsciiChar('D', 'green'),
    #             8: vectty.AsciiChar('E', 'green')
    #         },
    #         1: {
    #             0: vectty.AsciiChar('A', 'green'),
    #             1: vectty.AsciiChar('B', 'green'),
    #             4: vectty.AsciiChar('C', 'green'),
    #             6: vectty.AsciiChar('D', 'green'),
    #             8: vectty.AsciiChar('E', 'green')
    #         }
    #     }
    #
    #     svg_frame = animation._render_frame_fg(screen_buffer, line_height=1, group_id='frame_test')
    #     pass

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
        vectty.AsciiAnimation._serialize_css_dict(css)

    def test__buffer_difference(self):
        before_buffer = {
            0: {
                0: vectty.AsciiChar('A'),
                1: vectty.AsciiChar('B'),
                2: vectty.AsciiChar('C')
            },
            1: {
                0: vectty.AsciiChar('D')
            }
        }
        a = vectty.AsciiAnimation()
        with self.subTest(case='Self comparison'):
            diff_buffer = a._buffer_difference({}, {})
            self.assertEqual(diff_buffer, {})

            diff_buffer = a._buffer_difference(before_buffer, before_buffer)
            self.assertEqual(diff_buffer, {})

        with self.subTest(case='Change in text'):
            after_buffer = copy.deepcopy(before_buffer)
            after_buffer[0][2] = vectty.AsciiChar('E')

            diff_buffer = a._buffer_difference(before_buffer, after_buffer)
            self.assertEqual(diff_buffer, {0: after_buffer[0]})

        with self.subTest(case='Change in color'):
            after_buffer = copy.deepcopy(before_buffer)
            after_buffer[0][0] = vectty.AsciiChar('A', 'red')

            diff_buffer = a._buffer_difference(before_buffer, after_buffer)
            self.assertEqual(diff_buffer, {0: after_buffer[0]})

        with self.subTest(case='New character'):
            after_buffer = copy.deepcopy(before_buffer)
            after_buffer[1][1] = vectty.AsciiChar('A', 'red')

            diff_buffer = a._buffer_difference(before_buffer, after_buffer)
            self.assertEqual(diff_buffer, {1: after_buffer[1]})

        with self.subTest(case='New line'):
            after_buffer = copy.deepcopy(before_buffer)
            after_buffer[2] = {}
            after_buffer[2][0] = vectty.AsciiChar('A', 'red')

            diff_buffer = a._buffer_difference(before_buffer, after_buffer)
            self.assertEqual(diff_buffer, {2: after_buffer[2]})

        with self.subTest(case='Missing character'):
            after_buffer = copy.deepcopy(before_buffer)
            del after_buffer[0][0]

            diff_buffer = a._buffer_difference(before_buffer, after_buffer)
            self.assertEqual(diff_buffer, {0: after_buffer[0]})

        with self.subTest(case='Missing Line'):
            after_buffer = copy.deepcopy(before_buffer)
            del after_buffer[1]

            diff_buffer = a._buffer_difference(before_buffer, after_buffer)
            self.assertEqual(diff_buffer, {1: {0: vectty.AsciiChar()}})

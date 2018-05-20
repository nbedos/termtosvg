import copy
import unittest

from vectty import anim


class TestAnim(unittest.TestCase):
    def test_render_animation(self):
        pass

    def test__render_line_bg_colors(self):
        screen_line = {
            0: anim.AsciiChar('A', None, 'red'),
            1: anim.AsciiChar('A', None, 'red'),
            3: anim.AsciiChar('A', None, 'red'),
            4: anim.AsciiChar('A', None, 'blue'),
            6: anim.AsciiChar('A', None, 'blue'),
            7: anim.AsciiChar('A', None, 'blue'),
            8: anim.AsciiChar('A', None, 'green'),
            9: anim.AsciiChar('A', None, 'red'),
            10: anim.AsciiChar('A', None, 'red')
        }

        animation = anim.AsciiAnimation()
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
            0: anim.AsciiChar('A', 'red', None),
            1: anim.AsciiChar('B', 'blue', None),
            4: anim.AsciiChar('C', 'blue', None),
            6: anim.AsciiChar('D', 'green', None),
            8: anim.AsciiChar('E', 'green', None),
            9: anim.AsciiChar('F', 'green', None),
            10: anim.AsciiChar('G', 'green', None),
            11: anim.AsciiChar('H', 'red', None),
            20: anim.AsciiChar(' ', 'ungrouped')
        }

        with self.subTest(case='Content'):
            animation = anim.AsciiAnimation()
            line_def, line_use = animation._render_characters(screen_line, 1.23)

            sorted_tspans = sorted(line_def.elements, key=lambda x: x.text)
            [tspan_ah, tspan_bc, tspan_defg, tspan_space] = sorted_tspans
            self.assertEqual(tspan_ah.text, 'AH')
            self.assertEqual(tspan_ah.attribs['class'], 'red')
            self.assertEqual(tspan_ah.attribs['x'], '0ex 11ex')
            self.assertEqual(tspan_bc.text, 'BC')
            self.assertEqual(tspan_bc.attribs['class'], 'blue')
            self.assertEqual(tspan_bc.attribs['x'], '1ex 4ex')
            self.assertEqual(tspan_defg.text, 'DEFG')
            self.assertEqual(tspan_defg.attribs['class'], 'green')
            self.assertEqual(tspan_defg.attribs['x'], '6ex 8ex 9ex 10ex')

            self.assertEqual(line_use.attribs['y'], '1.23em')

        with self.subTest(case='Definition reuse'):
            animation = anim.AsciiAnimation()
            line_def_1, line_use_1 = animation._render_characters(screen_line, 1.23)
            line_def_2, line_use_2 = animation._render_characters(screen_line, 1.23)

            self.assertIsNone(line_def_2)
            self.assertEqual(line_use_1.tostring(), line_use_2.tostring())



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
        anim.AsciiAnimation._serialize_css_dict(css)


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
        animation = anim.AsciiAnimation()
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
        anim.AsciiAnimation._serialize_css_dict(css)

    def test__buffer_difference(self):
        before_buffer = {
            0: {
                0: anim.AsciiChar('A'),
                1: anim.AsciiChar('B'),
                2: anim.AsciiChar('C')
            },
            1: {
                0: anim.AsciiChar('D')
            }
        }
        a = anim.AsciiAnimation()
        with self.subTest(case='Self comparison'):
            diff_buffer = a._buffer_difference({}, {})
            self.assertEqual(diff_buffer, {})

            diff_buffer = a._buffer_difference(before_buffer, before_buffer)
            self.assertEqual(diff_buffer, {})

        with self.subTest(case='Change in text'):
            after_buffer = copy.deepcopy(before_buffer)
            after_buffer[0][2] = anim.AsciiChar('E')

            diff_buffer = a._buffer_difference(before_buffer, after_buffer)
            self.assertEqual(diff_buffer, {0: after_buffer[0]})

        with self.subTest(case='Change in color'):
            after_buffer = copy.deepcopy(before_buffer)
            after_buffer[0][0] = anim.AsciiChar('A', 'red')

            diff_buffer = a._buffer_difference(before_buffer, after_buffer)
            self.assertEqual(diff_buffer, {0: after_buffer[0]})

        with self.subTest(case='New character'):
            after_buffer = copy.deepcopy(before_buffer)
            after_buffer[1][1] = anim.AsciiChar('A', 'red')

            diff_buffer = a._buffer_difference(before_buffer, after_buffer)
            self.assertEqual(diff_buffer, {1: after_buffer[1]})

        with self.subTest(case='New line'):
            after_buffer = copy.deepcopy(before_buffer)
            after_buffer[2] = {}
            after_buffer[2][0] = anim.AsciiChar('A', 'red')

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
            self.assertEqual(diff_buffer, {1: {0: anim.AsciiChar()}})

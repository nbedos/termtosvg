import os
import tempfile
import unittest

import pyte.screens

from termtosvg import anim


class TestAnim(unittest.TestCase):
    def test_from_pyte(self):
        pyte_chars = [
            # Simple mapping
            pyte.screens.Char('A', 'red', 'blue'),
            # Reverse colors
            pyte.screens.Char('B', 'red', 'blue', reverse=True),
            # Bold for foreground -> bright colors
            pyte.screens.Char('C', 'red', 'blue', bold=True),
            # Bold and reverse
            pyte.screens.Char('D', 'red', 'blue', bold=True, reverse=True),
            # Bold with no matching bright color
            pyte.screens.Char('E', 'blue', 'blue', bold=True),
            # Defaults
            pyte.screens.Char('F', 'default', 'default'),
            # Hexadecimal
            pyte.screens.Char('G', '008700', 'ABCDEF'),
            # Bright and bold
            pyte.screens.Char('H', 'brightgreen', 'ABCDEF', bold=True),
            # Bright but not in the palette --> fallback to the non bright color
            # for compatibility with an 8-color palette (issue #1)
            pyte.screens.Char('I', 'brown', 'ABCDEF', bold=True),
            # Bright + bold and fallback to non bright
            pyte.screens.Char('J', 'brightbrown', 'ABCDEF', bold=True),
        ]

        char_cells = [
            anim.CharacterCell('A', 'color1', 'color4', False),
            anim.CharacterCell('B', 'color4', 'color1', False),
            anim.CharacterCell('C', 'color9', 'color4', True),
            anim.CharacterCell('D', 'color4', 'color9', True),
            anim.CharacterCell('E', 'color12', 'color4', True),
            anim.CharacterCell('F', 'foreground', 'background', False),
            anim.CharacterCell('G', '#008700', '#ABCDEF', False),
            anim.CharacterCell('H', 'color10', '#ABCDEF', True),
            anim.CharacterCell('I', 'color3', '#ABCDEF', True),
            anim.CharacterCell('J', 'color3', '#ABCDEF', True),
        ]

        palette = {
            'foreground': 'foreground',
            'background': 'background',
            1: 'color1',
            3: 'color3',
            4: 'color4',
            9: 'color9',
            10: 'color10',
            12: 'color12',
        }
        for pyte_char, cell_char in zip(pyte_chars, char_cells):
            with self.subTest(case=pyte_char):
                self.assertEqual(anim.CharacterCell.from_pyte(pyte_char, palette), cell_char)

    def test__render_line_bg_colors(self):
        cell_width = 8
        screen_line = {
            0: anim.CharacterCell('A', 'black', 'red', False),
            1: anim.CharacterCell('A', 'black', 'red', False),
            3: anim.CharacterCell('A', 'black', 'red', False),
            4: anim.CharacterCell('A', 'black', 'blue', False),
            6: anim.CharacterCell('A', 'black', 'blue', False),
            7: anim.CharacterCell('A', 'black', 'blue', False),
            8: anim.CharacterCell('A', 'black', 'green', False),
            9: anim.CharacterCell('A', 'black', 'red', False),
            10: anim.CharacterCell('A', 'black', 'red', False),
            99: anim.CharacterCell('A', 'black', 'black', False),
        }

        rectangles = anim._render_line_bg_colors(screen_line=screen_line,
                                                 height=0,
                                                 line_height=1,
                                                 cell_width=cell_width,
                                                 background_color='black')
        rect_0, rect_3, rect_4, rect_6, rect_8, rect_9 = sorted(rectangles,
                                                                key=lambda r: r.attribs['x'])

        self.assertEqual(rect_0.attribs['x'], 0)
        self.assertEqual(rect_0.attribs['width'], 16)
        self.assertEqual(rect_0.attribs['fill'], 'red')
        self.assertEqual(rect_3.attribs['x'], 24)
        self.assertEqual(rect_3.attribs['width'], 8)
        self.assertEqual(rect_4.attribs['x'], 32)
        self.assertEqual(rect_6.attribs['x'], 48)
        self.assertEqual(rect_6.attribs['width'], 16)
        self.assertEqual(rect_6.attribs['fill'], 'blue')
        self.assertEqual(rect_8.attribs['x'], 64)
        self.assertEqual(rect_8.attribs['fill'], 'green')
        self.assertEqual(rect_9.attribs['x'], 72)

    def test__render_characters(self):
        screen_line = {
            0: anim.CharacterCell('A', 'red', 'white', False),
            1: anim.CharacterCell('B', 'blue', 'white', False),
            2: anim.CharacterCell('C', 'blue', 'white', False),
            7: anim.CharacterCell('D', 'green', 'white', False),
            8: anim.CharacterCell('E', 'green', 'white', False),
            9: anim.CharacterCell('F', 'green', 'white', False),
            10: anim.CharacterCell('G', 'green', 'white', False),
            11: anim.CharacterCell('H', 'red', 'white', False),
            20: anim.CharacterCell(' ', 'black', 'black', False)
        }

        with self.subTest(case='Content'):
            cell_width = 8
            texts = anim._render_characters(screen_line, 1.23, cell_width)

            sorted_texts = sorted(texts, key=lambda x: x.text)
            [text_a, text_bc, text_defg, text_h, text_space] = sorted_texts
            self.assertEqual(text_a.text, 'A')
            self.assertEqual(text_a.attribs['fill'], 'red')
            self.assertEqual(text_a.attribs['x'], '0')
            self.assertEqual(text_bc.text, 'BC')
            self.assertEqual(text_bc.attribs['fill'], 'blue')
            self.assertEqual(text_bc.attribs['x'], '8')
            self.assertEqual(text_defg.text, 'DEFG')
            self.assertEqual(text_defg.attribs['fill'], 'green')
            self.assertEqual(text_defg.attribs['x'], '56')

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
        anim._serialize_css_dict(css)

    def test_render_animation(self):
        def line(i):
            chars = [anim.CharacterCell(c, '#123456', '#789012', False) for c in 'line{}'.format(i)]
            return dict(enumerate(chars))

        records = [
            anim.CharacterCellConfig(80, 24, 'black', 'black'),
            anim.CharacterCellLineEvent(1, line(1), 0, 60),
            anim.CharacterCellLineEvent(2, line(2), 60, 60),
            anim.CharacterCellLineEvent(3, line(3), 120, 60),
            anim.CharacterCellLineEvent(4, line(4), 180, 60),
            # Definition reuse
            anim.CharacterCellLineEvent(5, line(4), 240, 60),
            # Override line for animation chaining
            anim.CharacterCellLineEvent(5, line(6), 300, 60),
        ]

        _, filename = tempfile.mkstemp(prefix='termtosvg_')
        anim.render_animation(records, filename, 'DejaVu Sans Mono', True)
        os.remove(filename)

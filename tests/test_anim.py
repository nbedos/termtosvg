import io
import pkgutil
import tempfile
import unittest
from collections import namedtuple

import pyte.screens
from lxml import etree

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
            # Defaults
            pyte.screens.Char('E', 'default', 'default'),
            # Hexadecimal
            pyte.screens.Char('F', '008700', 'ABCDEF'),
            # Bright and bold
            pyte.screens.Char('G', 'brightgreen', 'ABCDEF', bold=True),
        ]

        char_cells = [
            anim.CharacterCell('A', 'color1', 'color4', False),
            anim.CharacterCell('B', 'color4', 'color1', False),
            anim.CharacterCell('C', 'color9', 'color4', True),
            anim.CharacterCell('D', 'color4', 'color9', True),
            anim.CharacterCell('E', 'foreground', 'background', False),
            anim.CharacterCell('F', '#008700', '#ABCDEF', False),
            anim.CharacterCell('G', 'color10', '#ABCDEF', True),
        ]

        for pyte_char, cell_char in zip(pyte_chars, char_cells):
            with self.subTest(case=pyte_char):
                self.assertEqual(anim.CharacterCell.from_pyte(pyte_char), cell_char)

    def test__render_line_bg_colors_xml(self):
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
            11: anim.CharacterCell('A', 'black', '#123456', False),
        }

        rectangles = anim._render_line_bg_colors(screen_line=screen_line,
                                                 height=0,
                                                 cell_height=1,
                                                 cell_width=cell_width)

        def key(r):
            return r.attrib['x']

        rect_0, rect_3, rect_4, rect_6, rect_8, rect_9, rect_11 = sorted(rectangles, key=key)

        self.assertEqual(rect_0.attrib['x'], '0')
        self.assertEqual(rect_0.attrib['width'], '16')
        self.assertEqual(rect_0.attrib['height'], '1')
        self.assertEqual(rect_0.attrib['class'], 'red')
        self.assertEqual(rect_3.attrib['x'], '24')
        self.assertEqual(rect_3.attrib['width'], '8')
        self.assertEqual(rect_4.attrib['x'], '32')
        self.assertEqual(rect_6.attrib['x'], '48')
        self.assertEqual(rect_6.attrib['width'], '16')
        self.assertEqual(rect_6.attrib['class'], 'blue')
        self.assertEqual(rect_8.attrib['x'], '64')
        self.assertEqual(rect_8.attrib['class'], 'green')
        self.assertEqual(rect_9.attrib['x'], '72')
        self.assertEqual(rect_11.attrib['fill'], '#123456')

    def test__render_characters(self):
        screen_line = {
            0: anim.CharacterCell('A', 'red', 'white', False),
            1: anim.CharacterCell('B', 'blue', 'white', False),
            2: anim.CharacterCell('C', 'blue', 'white', False),
            7: anim.CharacterCell('D', '#00FF00', 'white', False),
            8: anim.CharacterCell('E', '#00FF00', 'white', False),
            9: anim.CharacterCell('F', '#00FF00', 'white', False),
            10: anim.CharacterCell('G', '#00FF00', 'white', False),
            11: anim.CharacterCell('H', 'red', 'white', False),
            20: anim.CharacterCell(' ', 'black', 'black', False)
        }

        with self.subTest(case='Content'):
            cell_width = 8
            texts = anim._render_characters(screen_line, cell_width)

            sorted_texts = sorted(texts, key=lambda x: x.text)
            [text_a, text_bc, text_defg, text_h, text_space] = sorted_texts
            self.assertEqual(text_a.text, 'A')
            self.assertEqual(text_a.attrib['class'], 'red')
            self.assertEqual(text_a.attrib['x'], '0')
            self.assertEqual(text_bc.text, 'BC')
            self.assertEqual(text_bc.attrib['class'], 'blue')
            self.assertEqual(text_bc.attrib['x'], '8')
            self.assertEqual(text_defg.text, 'DEFG')
            self.assertEqual(text_defg.attrib['fill'], '#00FF00')
            self.assertEqual(text_defg.attrib['x'], '56')

    def test_ConsecutiveWithSameAttributes(self):
        testClass = namedtuple('testClass', ['field1', 'field2'])
        test_cases = [
            (0, testClass('a', 'b')),
            (2, testClass('a', 'b')),
            (3, testClass('a', 'b')),
            (4, testClass('b', 'b')),
            (5, testClass('b', 'a')),
            (10, testClass('c', 'd')),
            (11, testClass('c', 'd')),
        ]

        expected_results = [
            (0, {'field1': 'a', 'field2': 'b'}),
            (2, {'field1': 'a', 'field2': 'b'}),
            (2, {'field1': 'a', 'field2': 'b'}),
            (4, {'field1': 'b', 'field2': 'b'}),
            (5, {'field1': 'b', 'field2': 'a'}),
            (10, {'field1': 'c', 'field2': 'd'}),
            (10, {'field1': 'c', 'field2': 'd'}),
        ]

        key = anim.ConsecutiveWithSameAttributes(['field1', 'field2'])
        for case, result in zip(test_cases, expected_results):
            with self.subTest(case=case):
                self.assertEqual(key(case), result)

    def test_make_animated_group(self):
        def line(i):
            chars = [anim.CharacterCell(c, '#123456', '#789012', False) for c in 'line{}'.format(i)]
            return dict(enumerate(chars))

        records = [
            anim.CharacterCellLineEvent(1, line(1), None, None),
            anim.CharacterCellLineEvent(2, line(2), None, None),
            anim.CharacterCellLineEvent(3, line(3), None, None),
            anim.CharacterCellLineEvent(4, line(4), None, None),
            # Definition reuse
            anim.CharacterCellLineEvent(5, line(4), None, None),
        ]

        group, new_defs = anim.make_animated_group(records=records,
                                                   time=10,
                                                   duration=1,
                                                   cell_width=8,
                                                   cell_height=17,
                                                   defs={})

    def test__render_animation(self):
        def line(i):
            chars = [anim.CharacterCell(c, '#123456', '#789012', False) for c in 'line{}'.format(i)]
            return dict(enumerate(chars))

        records = [
            anim.CharacterCellConfig(80, 24),
            anim.CharacterCellLineEvent(1, line(1), 0, 60),
            anim.CharacterCellLineEvent(2, line(2), 60, 60),
            anim.CharacterCellLineEvent(3, line(3), 120, 60),
            anim.CharacterCellLineEvent(4, line(4), 180, 60),
            # Definition reuse
            anim.CharacterCellLineEvent(5, line(4), 240, 60),
            # Override line for animation chaining
            anim.CharacterCellLineEvent(5, line(6), 300, 60),
        ]
        template = pkgutil.get_data('termtosvg', '/data/templates/progress_bar.svg')
        svg_root = anim._render_animation(records, template, 8, 17)

        _, filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.svg')
        with open(filename, 'wb') as f:
            f.write(etree.tostring(svg_root))

    def test_add_css_variables(self):
        data = pkgutil.get_data('termtosvg', '/data/templates/progress_bar.svg')

        tree = etree.parse(io.BytesIO(data))
        root = tree.getroot()
        anim.add_css_variables(root, 42)

    def test_validate_svg(self):
        failure_test_cases = [
            '',
            '<svg>',
            '</svg>',
            '<svg></a>',
            None,
        ]
        for case in failure_test_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    anim.validate_svg(io.StringIO(case))



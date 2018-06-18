import logging
import os
from collections import namedtuple
from itertools import groupby
from typing import Dict, List, Iterable, Iterator, Union, Tuple, Any

import pyte.graphics
import pyte.screens
import svgwrite.animate
import svgwrite.container
import svgwrite.path
import svgwrite.shapes
import svgwrite.text

# Ugliest hack: Replace the first 16 colors rgb values by their names so that termtosvg can
# distinguish FG_BG_256[0] (which defaults to black #000000 but can be styled with e.g. Xresources)
# from FG_BG_256[16] (which is also black #000000 but should be displayed as is).
colors = ['black', 'red', 'green', 'brown', 'blue', 'magenta', 'cyan', 'white']
brightcolors = ['bright{}'.format(color) for color in colors]
pyte.graphics.FG_BG_256 = colors + brightcolors + pyte.graphics.FG_BG_256[16:]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

_CharacterCell = namedtuple('_CharacterCell', ['text', 'color', 'background_color'])
_CharacterCell.__doc__ = 'Representation of a character cell'
_CharacterCell.text.__doc__ = 'Text content of the cell'
_CharacterCell.color.__doc__ = 'Color of the text'
_CharacterCell.background_color.__doc__ = 'Background color of the cell'


class CharacterCell(_CharacterCell):
    @classmethod
    def from_pyte(cls, char, palette):
        # type: (pyte.screens.Char, Dict[Any, str]) -> CharacterCell
        """Create a CharacterCell from a pyte character"""
        # Mappings between colors from Pyte and colors in the palette
        all_colors = colors + brightcolors
        # Map named colors to their respective number
        color_numbers = dict(zip(all_colors, range(len(all_colors))))
        if char.fg == 'default':
            text_color = palette['foreground']
        else:
            if char.bold and not str(char.fg).startswith('bright'):
                search_color = 'bright{}'.format(char.fg)
            else:
                search_color = char.fg

            if search_color in color_numbers and color_numbers[search_color] in palette:
                # Named colors
                text_color = palette[color_numbers[search_color]]
            elif len(char.fg) == 6:
                # Hexadecimal colors
                # raise ValueError if char.bg hexadecimal number
                int(char.fg, 16)
                text_color = '#{}'.format(char.fg)
            else:
                raise ValueError('Invalid foreground color: {}'.format(char.fg))

        if char.bg == 'default':
            # Default colors
            background_color = palette['background']
        elif char.bg in color_numbers:
            # Named colors
            background_color = palette[color_numbers[char.bg]]
        elif len(char.bg) == 6:
            # Hexadecimal colors
            # raise ValueError if char.bg hexadecimal number
            int(char.bg, 16)
            background_color = '#{}'.format(char.bg)
        else:
            raise ValueError('Invalid background color')

        if char.reverse:
            text_color, background_color = background_color, text_color

        return CharacterCell(char.data, text_color, background_color)


CharacterCellConfig = namedtuple('CharacterCellConfig', ['width', 'height', 'text_color',
                                                         'background_color'])
CharacterCellLineEvent = namedtuple('CharacterCellLineEvent', ['row', 'line', 'time', 'duration'])
CharacterCellRecord = Union[CharacterCellConfig, CharacterCellLineEvent]


def _render_line_bg_colors(screen_line, height, line_height, cell_width, background_color):
    # type: (Dict[int, CharacterCell], float, float) -> List[svgwrite.shapes.Rect]
    def make_rectangle(group: List[int]) -> svgwrite.shapes.Rect:
        x = group[0] * cell_width
        y = height
        sx = len(group) * cell_width
        sy = line_height
        args = {
            'insert': (x, y),
            'size': (sx, sy),
            'fill': screen_line[group[0]].background_color
        }
        return svgwrite.shapes.Rect(**args)

    group = []
    groups = []
    cols = {col for col in screen_line if screen_line[col].background_color is not None}
    for index in sorted(cols):
        group.append(index)
        if index + 1 not in screen_line or \
                screen_line[index].background_color != screen_line[index + 1].background_color:
            if screen_line[index].background_color != background_color:
                groups.append(group)
            group = []

    rectangles = [make_rectangle(group) for group in groups]
    return rectangles


def _render_characters(screen_line, height, cell_width):
    # type: (Dict[int, CharacterCell], float) -> List[svgwrite.text.Tspan]
    """Render a screen of the terminal as a list of SVG text elements

    Characters with the same attributes (color) are grouped together in a
    single text element.

    :param screen_line: Mapping between positions on the row and characters
    :param height: Vertical position of the line
    :return: List of SVG text elements
    """

    def make_text(group: List[int]) -> svgwrite.text.Text:
        text = ''.join(screen_line[c].text for c in group)
        attributes = {
            'text': text.replace(' ', u'\u00A0'),
            'x': [str(group[0] * cell_width)],
            'textLength': len(group) * cell_width,
            'lengthAdjust': 'spacingAndGlyphs',
            'fill': screen_line[group[0]].color
        }
        return svgwrite.text.Text(**attributes)

    group = []
    groups = []
    cols = {col for col in screen_line if screen_line[col].background_color is not None}
    for col in sorted(cols):
        group.append(col)
        if col + 1 not in screen_line or \
                screen_line[col].color != screen_line[col+1].color:
            groups.append(group)
            group = []

    texts = [make_text(group) for group in groups]
    return texts


def render_animation(records, filename, end_pause=1, cell_width=8, cell_height=17):
    # type: (Iterable[CharacterCellRecord], str, int) -> None
    if end_pause < 0:
        raise ValueError('Invalid end_pause (must be >= 0): "{}"'.format(end_pause))

    if not isinstance(records, Iterator):
        records = iter(records)

    header = next(records)

    font_size = 14
    css = {
        # Apply this style to each and every element since we are using coordinates that
        # depend on the size of the font
        '*': {
            'font-family': '"DejaVu Sans Mono", monospace',
            'font-style': 'normal',
            'font-size': '{}px'.format(font_size),
        },
        'text': {
            'dominant-baseline': 'text-before-edge',
        },
        '.bold': {
            'font-weight': 'bold',
        },
        '.background': {
            'fill': header.background_color,
        },
    }

    width = header.width * cell_width
    height = header.height * cell_height

    dwg = svgwrite.Drawing(filename, (width, height), debug=True)
    dwg.defs.add(dwg.style(_serialize_css_dict(css)))
    args = {
        'insert': (0, 0),
        'size': ('100%', '100%'),
        'class': 'background'
    }
    r = svgwrite.shapes.Rect(**args)
    dwg.add(r)

    def by_time(record: CharacterCellRecord) -> Tuple[int, int]:
        return record.time, record.duration

    row_animations = {}
    definitions = {}
    last_animation_id_str = 'anim_last'
    animation = None
    for animation_id, (key, record_group) in enumerate(groupby(records, key=by_time)):
        line_time, line_duration = key
        frame = svgwrite.container.Group(display='none')

        animation_begin = None
        animation_id_str = 'anim_{}'.format(animation_id)
        for event_record in record_group:
            height = event_record.row * cell_height
            rects = _render_line_bg_colors(event_record.line,
                                           height,
                                           cell_height,
                                           cell_width,
                                           header.background_color)
            for rect in rects:
                frame.add(rect)

            g = svgwrite.container.Group()
            for text in _render_characters(event_record.line, height, cell_width):
                g.add(text)

            # Define this line or reuse the existing definition
            g_str = g.tostring()
            if g_str in definitions:
                group_id = definitions[g_str]
            else:
                group_id = len(definitions) + 1
                assert group_id not in definitions
                definitions[g_str] = group_id
                g.attribs['id'] = group_id
                dwg.defs.add(g)

            frame.add(svgwrite.container.Use('#{}'.format(group_id), y=height))

            # If the current row has already been animated, chain the current animation and the
            # last one
            if animation_begin is None and event_record.row in row_animations:
                row_anim_id, row_anim_end = row_animations[event_record.row]
                offset = line_time - row_anim_end
                animation_begin = '{}.end+{}ms'.format(row_anim_id, offset)

            row_animations[event_record.row] = (animation_id_str, line_time + line_duration)

        if animation_begin is None:
            animation_begin = '{}ms;{}.end+{}ms'.format(line_time, last_animation_id_str, line_time)

        extra = {
            'begin': animation_begin,
            'dur': '{}ms'.format(line_duration),
            'from': 'inline',
            'to': 'inline',
            'fill': 'remove',
            'id': animation_id_str
        }

        animation = svgwrite.animate.Animate('display', **extra)
        frame.add(animation)

        dwg.add(frame)

    animation.attribs['id'] = last_animation_id_str
    dwg.save()


def _serialize_css_dict(css):
    # type: (Dict[str, Dict[str, str]]) -> str
    def serialize_css_item(item):
        return '; '.join('{}: {}'.format(prop, item[prop]) for prop in item)

    items = ['{} {{{}}}'.format(item, serialize_css_item(css[item])) for item in css]
    return os.linesep.join(items)

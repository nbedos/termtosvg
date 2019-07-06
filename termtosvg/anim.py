import copy
import io
import os.path
import pkgutil
from collections import namedtuple
from itertools import groupby

import pyte.graphics
import pyte.screens
from lxml import etree
from wcwidth import wcswidth

# Ugliest hack: Replace the first 16 colors rgb values by their names so that
# termtosvg can distinguish FG_BG_256[0] (which defaults to black #000000 but
# can be styled with themes) from FG_BG_256[16] (which is also black #000000
# but should be displayed as is).
_COLORS = ['black', 'red', 'green', 'brown', 'blue', 'magenta', 'cyan', 'white']
_BRIGHTCOLORS = ['bright{}'.format(color) for color in _COLORS]
NAMED_COLORS = _COLORS + _BRIGHTCOLORS
pyte.graphics.FG_BG_256 = NAMED_COLORS + pyte.graphics.FG_BG_256[16:]

# Id for the very last SVG animation. This is used to make the first animations
# start when the last one ends (animation looping)
LAST_ANIMATION_ID = 'anim_last'

# Background rectangle SVG element
_BG_RECT_TAG_ATTRIBUTES = {
    'class': 'background',
    'height': '100%',
    'width': '100%',
    'x': '0',
    'y': '0'
}
BG_RECT_TAG = etree.Element('rect', _BG_RECT_TAG_ATTRIBUTES)

# Default size for a character cell rendered as SVG.
CELL_WIDTH = 8
CELL_HEIGHT = 17

# The number of character cells to leave when placing successive frames
# so content does not bleed into adjacent frames
FRAME_CELL_SPACING = 1

# XML namespaces
SVG_NS = 'http://www.w3.org/2000/svg'
TERMTOSVG_NS = 'https://github.com/nbedos/termtosvg'
XLINK_NS = 'http://www.w3.org/1999/xlink'

NAMESPACES = {
    'svg': SVG_NS,
    'termtosvg': TERMTOSVG_NS,
    'xlink': XLINK_NS,
}


class TemplateError(Exception):
    pass


_CELL_ATTRIBUTES = ['text', 'color', 'background_color', 'bold', 'italics',
                    'underscore', 'strikethrough']
_CharacterCell = namedtuple('_CharacterCell', _CELL_ATTRIBUTES)
# Set default values for last 6 arguments
_CharacterCell.__new__.__defaults__ = ('foreground', 'background', False, False,
                                       False, False)
_CharacterCell.__doc__ = 'Representation of a character cell'
_CharacterCell.text.__doc__ = 'Text content of the cell'
_CharacterCell.bold.__doc__ = 'Bold modificator flag'
_CharacterCell.italics.__doc__ = 'Italics modificator flag'
_CharacterCell.underscore.__doc__ = 'Underscore modificator flag'
_CharacterCell.strikethrough.__doc__ = 'Strikethrough modificator flag'
_CharacterCell.color.__doc__ = 'Color of the text'
_CharacterCell.background_color.__doc__ = 'Background color of the cell'


class CharacterCell(_CharacterCell):
    @classmethod
    def from_pyte(cls, char):
        """Create a CharacterCell from a pyte character"""
        if char.fg == 'default':
            text_color = 'foreground'
        else:
            if char.bold and not str(char.fg).startswith('bright'):
                named_color = 'bright{}'.format(char.fg)
            else:
                named_color = char.fg

            if named_color in NAMED_COLORS:
                text_color = 'color{}'.format(NAMED_COLORS.index(named_color))
            elif len(char.fg) == 6:
                # HEXADECIMAL COLORS
                # raise ValueError if char.fg is not an hexadecimal number
                int(char.fg, 16)
                text_color = '#{}'.format(char.fg)
            else:
                raise ValueError('Invalid foreground color: {}'.format(char.fg))

        if char.bg == 'default':
            background_color = 'background'
        elif char.bg in NAMED_COLORS:
            background_color = 'color{}'.format(NAMED_COLORS.index(char.bg))
        elif len(char.bg) == 6:
            # Hexadecimal colors
            # raise ValueError if char.bg is not an hexadecimal number
            int(char.bg, 16)
            background_color = '#{}'.format(char.bg)
        else:
            raise ValueError('Invalid background color')

        if char.reverse:
            text_color, background_color = background_color, text_color

        return CharacterCell(char.data, text_color, background_color,
                             char.bold, char.italics, char.underscore,
                             char.strikethrough)


class ConsecutiveWithSameAttributes:
    """Callable to be used as a key for itertools.groupby to group together
    consecutive elements of a list with the same attributes"""
    def __init__(self, attributes):
        self.group_index = None
        self.last_index = None
        self.attributes = attributes
        self.last_key_attributes = None

    def __call__(self, arg):
        index, obj = arg
        key_attributes = {name: getattr(obj, name) for name in self.attributes}
        if self.last_index != index - 1 or self.last_key_attributes != key_attributes:
            self.group_index = index
        self.last_index = index
        self.last_key_attributes = key_attributes
        return self.group_index, key_attributes


def render_animation(frames, geometry, filename, template,
                     cell_width=CELL_WIDTH, cell_height=CELL_HEIGHT):
    root = _render_preparation(geometry, template, cell_width, cell_height)
    _, screen_height = geometry
    root = _render_animation(screen_height, frames, root, cell_width, cell_height)

    with open(filename, 'wb') as output_file:
        output_file.write(etree.tostring(root))


def render_still_frames(frames, geometry, directory, template,
                        cell_width=CELL_WIDTH, cell_height=CELL_HEIGHT):
    root = _render_preparation(geometry, template, cell_width, cell_height)

    frame_generator = _render_still_frames(frames, root, cell_width, cell_height)
    for frame_count, frame_root in enumerate(frame_generator):
        filename = os.path.join(directory, 'termtosvg_{:05}.svg'.format(frame_count))
        with open(filename, 'wb') as output_file:
            output_file.write(etree.tostring(frame_root))


def _render_preparation(geometry, template, cell_width, cell_height):
    # Read header record and add the corresponding information to the SVG
    root = resize_template(template, geometry, cell_width, cell_height)
    svg_screen_tag = root.find('.//{{{namespace}}}svg[@id="screen"]'
                               .format(namespace=SVG_NS))
    if svg_screen_tag is None:
        raise ValueError('Missing tag: <svg id="screen" ...>...</svg>')

    for child in svg_screen_tag.getchildren():
        svg_screen_tag.remove(child)
    svg_screen_tag.append(BG_RECT_TAG)

    return root


def _render_still_frames(frames, root, cell_width, cell_height):
    for frame in frames:
        frame_group, frame_definitions = _render_timed_frame(
            offset=0,
            buffer=frame.buffer,
            cell_height=cell_height,
            cell_width=cell_width,
            definitions={}
        )
        frame_root = copy.deepcopy(root)
        svg_screen_tag = frame_root.find('.//{{{namespace}}}svg[@id="screen"]'
                                         .format(namespace=SVG_NS))
        if svg_screen_tag is None:
            raise ValueError('Missing tag: <svg id="screen" ...>...</svg>')
        tree_defs = etree.SubElement(svg_screen_tag, 'defs')
        for definition in frame_definitions.values():
            tree_defs.append(definition)
        svg_screen_tag.append(frame_group)

        _embed_css(frame_root)
        yield frame_root


def _render_animation(screen_height, frames, root, cell_width, cell_height):
    svg_screen_tag = root.find('.//{{{namespace}}}svg[@id="screen"]'
                               .format(namespace=SVG_NS))
    if svg_screen_tag is None:
        raise ValueError('Missing tag: <svg id="screen" ...>...</svg>')

    screen_view = etree.Element('g', attrib={'id': 'screen_view'})

    definitions = {}
    timings = {}
    animation_duration = None
    for frame_count, frame in enumerate(frames):
        # To prevent line jumping up and down by one pixel between two frames,
        # add h % 2 so that offset is an even number.  (issue noticed in
        # Firefox only)
        h = screen_height + FRAME_CELL_SPACING
        offset = frame_count * (h + h % 2) * cell_height
        frame_group, frame_definitions = _render_timed_frame(
            offset=offset,
            buffer=frame.buffer,
            cell_height=cell_height,
            cell_width=cell_width,
            definitions=definitions
        )

        screen_view.append(frame_group)
        animation_duration = frame.time + frame.duration
        timings[frame.time] = -offset
        definitions.update(frame_definitions)

    tree_defs = etree.SubElement(svg_screen_tag, 'defs')
    for definition in definitions.values():
        tree_defs.append(definition)

    svg_screen_tag.append(screen_view)
    _add_animation(root, timings, animation_duration)
    return root


def _add_animation(root, timings, animation_duration):
    animators = {
        'css': _embed_css,
        'waapi': _embed_waapi,
    }

    settings = root.find('.//{{{}}}defs/{{{}}}template_settings'
                         .format(SVG_NS, TERMTOSVG_NS))
    if settings is None:
        raise TemplateError('Missing "template_settings" element in definitions')

    animation = settings.find('{{{}}}animation[@type]'.format(TERMTOSVG_NS))
    if animation is None:
        raise TemplateError('Missing or invalid "animation" element in "template_settings"')

    f = animators.get(animation.attrib['type'].lower())
    if f is None:
        raise TemplateError("Attribute 'type' of element 'animation' must be one of {}"
                            .format(', '.join(animators.keys())))

    f(root, timings, animation_duration)


def _render_timed_frame(offset, buffer, cell_height, cell_width, definitions):
    """Return a group element containing an SVG version of the provided frame.

    :param buffer: 2D array of CharacterCells
    :param cell_height: Height of a character cell in pixels
    :param cell_width: Width of a character cell in pixels
    :param definitions: Existing definitions (updated in place)
    :return: A tuple consisting of a group element and new definitions
    """
    frame_group_tag = etree.Element('g')

    group_definitions = {}
    for row_number in buffer:
        if buffer[row_number]:
            current_definitions = {**definitions, **group_definitions}
            tags, new_definitions = _render_line(offset,
                                                 row_number,
                                                 buffer[row_number],
                                                 cell_height,
                                                 cell_width,
                                                 current_definitions)
            for tag in tags:
                frame_group_tag.append(tag)
            group_definitions.update(new_definitions)

    return frame_group_tag, group_definitions


def _render_line(offset, row_number, row, cell_height, cell_width, definitions):
    tags = _render_line_bg_colors(screen_line=row,
                                  height=offset + row_number * cell_height,
                                  cell_height=cell_height,
                                  cell_width=cell_width)

    # Group text elements for the current line into text_group_tag
    text_group_tag = etree.Element('g')
    text_tags = _render_characters(row, cell_width)
    for tag in text_tags:
        text_group_tag.append(tag)

    # Find or create a definition for text_group_tag
    text_group_tag_str = etree.tostring(text_group_tag)
    if text_group_tag_str in definitions:
        group_id = definitions[text_group_tag_str].attrib['id']
        new_definitions = {}
    else:
        group_id = 'g{}'.format(len(definitions) + 1)
        assert group_id not in definitions.values()
        text_group_tag.attrib['id'] = group_id
        new_definitions = {text_group_tag_str: text_group_tag}

    # Add a reference to the definition of text_group_tag with a 'use' tag
    use_attributes = {
        '{{{}}}href'.format(XLINK_NS): '#{}'.format(group_id),
        'y': str(offset + row_number * cell_height),
    }
    tags.append(etree.Element('use', use_attributes))

    return tags, new_definitions


def _make_rect_tag(column, length, height, cell_width, cell_height, background_color):
    attributes = {
        'x': str(column * cell_width),
        'y': str(height),
        'width': str(length * cell_width),
        'height': str(cell_height)
    }

    if background_color.startswith('#'):
        attributes['fill'] = background_color
    else:
        attributes['class'] = background_color
    rect_tag = etree.Element('rect', attributes)
    return rect_tag


def _render_line_bg_colors(screen_line, height, cell_height, cell_width):
    """Return a list of 'rect' tags representing the background of 'screen_line'

    If consecutive cells have the same background color, a single 'rect' tag is
    returned for all these cells.
    If a cell background uses default_bg_color, no 'rect' will be generated for
    this cell since the default background is always displayed.

    :param screen_line: Mapping between column numbers and CharacterCells
    :param height: Vertical position of the line on the screen in pixels
    :param cell_height: Height of the a character cell in pixels
    :param cell_width: Width of a character cell in pixels
    """
    non_default_bg_cells = [(column, cell) for (column, cell)
                            in sorted(screen_line.items())
                            if cell.background_color != 'background']

    key = ConsecutiveWithSameAttributes(['background_color'])
    rect_tags = [
        _make_rect_tag(
            column,
            wcswidth(''.join(t[1].text for t in group)),
            height,
            cell_width,
            cell_height,
            attributes['background_color']
        ) for (column, attributes), group in groupby(non_default_bg_cells, key)]

    return rect_tags


def _make_text_tag(column, attributes, text, cell_width):
    """Build SVG text element based on content and style attributes"""
    text_tag_attributes = {
        'x': str(column * cell_width),
        'textLength': str(wcswidth(text) * cell_width),
    }
    if attributes['bold']:
        text_tag_attributes['font-weight'] = 'bold'

    if attributes['italics']:
        text_tag_attributes['font-style'] = 'italic'

    decoration = ''
    if attributes['underscore']:
        decoration = 'underline'
    if attributes['strikethrough']:
        decoration += ' line-through'
    if decoration:
        text_tag_attributes['text-decoration'] = decoration

    if attributes['color'].startswith('#'):
        text_tag_attributes['fill'] = attributes['color']
    else:
        text_tag_attributes['class'] = attributes['color']

    text_tag = etree.Element('text', text_tag_attributes)
    text_tag.text = text
    return text_tag


def _render_characters(screen_line, cell_width):
    """Return a list of 'text' elements representing the line of the screen

    Consecutive characters with the same styling attributes (text color, font
    weight...) are grouped together in a single text element.

    :param screen_line: Mapping between column numbers and characters
    :param cell_width: Width of a character cell in pixels
    """
    line = sorted(screen_line.items())
    key = ConsecutiveWithSameAttributes(['color', 'bold', 'italics', 'underscore', 'strikethrough'])
    text_tags = [_make_text_tag(column, attributes, ''.join(c.text for _, c in group), cell_width)
                 for (column, attributes), group in groupby(line, key)]

    return text_tags


def resize_template(template, geometry, cell_width, cell_height):
    """Resize template based on the number of rows and columns of the terminal"""
    def scale(element, template_columns, template_rows, columns, rows):
        """Resize viewbox based on the number of rows and columns of the terminal"""
        try:
            viewbox = element.attrib['viewBox'].replace(',', ' ').split()
        except KeyError:
            raise TemplateError('Missing "viewBox" for element "{}"'.format(element))

        vb_min_x, vb_min_y, vb_width, vb_height = [int(n) for n in viewbox]
        vb_width += cell_width * (columns - template_columns)
        vb_height += cell_height * (rows - template_rows)
        element.attrib['viewBox'] = ' '.join(map(str, (vb_min_x, vb_min_y, vb_width, vb_height)))

        scalable_attributes = {
            'width': cell_width * (columns - template_columns),
            'height': cell_height * (rows - template_rows)
        }

        for attribute, delta in scalable_attributes.items():
            if attribute in element.attrib:
                try:
                    element.attrib[attribute] = str(int(element.attrib[attribute]) + delta)
                except ValueError:
                    raise TemplateError('"{}" attribute of {} must be in user units'
                                        .format(attribute, element))
        return element

    try:
        tree = etree.parse(io.BytesIO(template))
        root = tree.getroot()
    except etree.Error as exc:
        raise TemplateError('Invalid template') from exc

    # Extract the screen geometry which is saved in a private data portion of
    # the template
    settings = root.find('.//{{{}}}defs/{{{}}}template_settings'
                         .format(SVG_NS, TERMTOSVG_NS))
    if settings is None:
        raise TemplateError('Missing "template_settings" element in definitions')

    svg_geometry = settings.find('{{{}}}screen_geometry[@columns][@rows]'
                                 .format(TERMTOSVG_NS))
    if svg_geometry is None:
        raise TemplateError('Missing "screen_geometry" element in "template_settings"')

    attributes_err_msg = ('Missing or invalid "columns" or "rows" attribute '
                          'for element "screen_geometry": expected positive '
                          'integers')
    try:
        template_columns = int(svg_geometry.attrib['columns'])
        template_rows = int(svg_geometry.attrib['rows'])
    except (KeyError, ValueError) as exc:
        raise TemplateError(attributes_err_msg) from exc

    # Update settings with real columns and rows values to preserve the scale
    # in case the animation serves as a template
    columns, rows = geometry
    svg_geometry.attrib['columns'], svg_geometry.attrib['rows'] = (str(columns),
                                                                   str(rows))

    if template_rows <= 0 or template_columns <= 0:
        raise TemplateError(attributes_err_msg)

    # Scale the viewBox of the root svg element based on the size of the screen
    # and the size registered in the template
    scale(root, template_columns, template_rows, columns, rows)

    # Also scale the viewBox of the svg element with id 'screen'
    screen = root.find('.//{{{namespace}}}svg[@id="screen"]'
                       .format(namespace=SVG_NS))
    if screen is None:
        raise TemplateError('svg element with id "screen" not found')
    scale(screen, template_columns, template_rows, columns, rows)

    return root


def validate_template(name, templates):
    if name in templates:
        return templates[name]

    try:
        with open(name, 'rb') as template_file:
            return template_file.read()
    except FileNotFoundError as exc:
        raise TemplateError('Invalid template') from exc


def _embed_css(root, timings=None, animation_duration=None):
    try:
        style = root.find('.//{{{ns}}}defs/{{{ns}}}style[@id="generated-style"]'
                          .format(ns=SVG_NS))
    except etree.Error as exc:
        raise TemplateError('Invalid template') from exc

    if style is None:
        raise TemplateError('Missing <style id="generated-style" ...> element '
                            'in "defs"')

    css_body = """#screen {
                font-family: 'DejaVu Sans Mono', monospace;
                font-style: normal;
                font-size: 14px;
            }

        text {
            dominant-baseline: text-before-edge;
            white-space: pre;
        }
    """

    if animation_duration is None or timings is None:
        style.text = etree.CDATA(css_body)
    else:
        if animation_duration == 0:
            raise ValueError('Animation duration must be greater than 0')

        transforms = []
        last_offset = None
        transform_format = "{time:.3f}%{{transform:translateY({offset}px)}}"
        for time, offset in sorted(timings.items()):
            transforms.append(
                transform_format.format(
                    time=100.0 * time/animation_duration,
                    offset=offset
                )
            )
            last_offset = offset

        if last_offset is not None:
            transforms.append(
                transform_format.format(time=100, offset=last_offset)
            )

        css_animation = """
            :root {{
                --animation-duration: {duration}ms;
            }}

            @keyframes roll {{
                {transforms}
            }}

            #screen_view {{
                animation-duration: {duration}ms;
                animation-iteration-count:infinite;
                animation-name:roll;
                animation-timing-function: steps(1,end);
                animation-fill-mode: forwards;
            }}
        """.format(
            duration=animation_duration,
            transforms=os.linesep.join(transforms)
        )

        style.text = etree.CDATA(css_body + css_animation)

    return root


def _embed_waapi(root, timings=None, animation_duration=None):
    try:
        style = root.find('.//{{{ns}}}defs/{{{ns}}}style[@id="generated-style"]'
                          .format(ns=SVG_NS))
    except etree.Error as exc:
        raise TemplateError('Invalid template') from exc

    if style is None:
        raise TemplateError('Missing <style id="generated-style" ...> element '
                            'in "defs"')

    css_body = """
        #screen {
            font-family: 'DejaVu Sans Mono', monospace;
            font-style: normal;
            font-size: 14px;
        }

        text {
            dominant-baseline: text-before-edge;
            white-space: pre;
        }
    """

    style.text = etree.CDATA(css_body)

    if animation_duration and timings:
        if animation_duration == 0:
            raise ValueError('Animation duration must be greater than 0')

        css_body += """
        :root {{
            --animation-duration: {duration}ms;
        }}

        """.format(duration=animation_duration)

        script_element = root.find('.//{{{ns}}}script[@id="generated-js"]'
                                   .format(ns=SVG_NS))
        if script_element is None:
            raise TemplateError(
                'Missing <script id="generated-js" ...> element')


        transform_no_offset = "{{transform: 'translate3D(0, {y_pos}px, 0)', easing: 'steps(1, end)'}}"
        transform_with_offset = "{{transform: 'translate3D(0, {y_pos}px, 0)', easing: 'steps(1, end)', offset: {offset:.3f}}}"

        transforms = []
        last_pos = None
        for time, y_pos in sorted(timings.items()):
            if last_pos is None:
                transforms.append(transform_no_offset.format(y_pos=y_pos))
            else:
                transforms.append(
                    transform_with_offset
                    .format(offset=time / animation_duration, y_pos=y_pos)
                )
            last_pos = y_pos

        if last_pos is not None:
            transforms.append(transform_no_offset.format(y_pos=last_pos))

        js_animation = """
        var termtosvg_vars = {{
            transforms: [
                {transforms}
            ],
            timings: {{
                duration: {duration},
                iterations: Infinity
            }}
        }};""".format(
            transforms=',{}'.format(os.linesep).join(transforms),
            duration=animation_duration
        )

        script_element.text = etree.CDATA(js_animation)

    return root


def validate_svg(svg_file):
    """Validate an SVG file against SVG 1.1 Document Type Definition"""
    package = __name__.split('.')[0]
    dtd_bytes = pkgutil.get_data(package, '/data/svg11-flat-20110816.dtd')
    with io.BytesIO(dtd_bytes) as bstream:
        dtd = etree.DTD(bstream)

    try:
        tree = etree.parse(svg_file)
        for bad in tree.xpath('/svg:svg/svg:defs/termtosvg:template_settings',
                              namespaces=NAMESPACES):
            bad.getparent().remove(bad)
        root = tree.getroot()
        is_valid = dtd.validate(root)
    except etree.Error as exc:
        raise ValueError('Invalid SVG file') from exc

    if not is_valid:
        reason = dtd.error_log.filter_from_errors()[0]
        raise ValueError('Invalid SVG file: {}'.format(reason))

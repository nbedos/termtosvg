"""Asciicast v2 record formats

Full specification: https://github.com/asciinema/asciinema/blob/develop/doc/asciicast-v2.md
"""
import abc
import codecs
import json
from collections import namedtuple
from Xlib import rdb

utf8_decoder = codecs.getincrementaldecoder('utf-8')('replace')


class AsciiCastRecord(abc.ABC):
    """Generic Asciicast v2 record format"""
    @abc.abstractmethod
    def to_json_line(self):
        raise NotImplementedError

    @classmethod
    def from_json_line(cls, line):
        if type(json.loads(line)) == dict:
            return AsciiCastHeader.from_json_line(line)
        elif type(json.loads(line)) == list:
            return AsciiCastEvent.from_json_line(line)
        else:
            raise NotImplementedError


_AsciiCastTheme = namedtuple('AsciiCastTheme', ['fg', 'bg', 'palette'])


class AsciiCastTheme(_AsciiCastTheme):
    """Color theme of the terminal.

    All colors must use the '#rrggbb' format

    fg: default text color
    bg: default background colors
    palette: colon separated list of 8 or 16 terminal colors
    """
    def __new__(cls, fg, bg, palette):
        if cls.is_color(fg):
            if cls.is_color(bg):
                colors = palette.split(':')
                if all([cls.is_color(c) for c in colors[:16]]):
                    self = super().__new__(cls, fg, bg, palette)
                    return self
                elif all([cls.is_color(c) for c in colors[:8]]):
                    new_palette = ':'.join(colors[:8])
                    self = super().__new__(cls, fg, bg, new_palette)
                    return self
                else:
                    raise ValueError('Invalid palette: the first 8 or 16 colors must be valid')
            else:
                raise ValueError('Invalid background color: {}'.format(bg))
        else:
            raise ValueError('Invalid foreground color: {}'.format(fg))

    @classmethod
    def from_xresources(cls, xresources):
        # type: (str) -> AsciiCastTheme
        """Parse the Xresources string and return an AsciiCastTheme containing the color information

        Raise ValueError if no theme could be created
        """
        res_db = rdb.ResourceDB(string=xresources)

        colors = {}
        names = [('foreground', True), ('background', True)] + \
                [('color{}'.format(index), index < 8) for index in range(16)]
        for name, required in names:
            res_name = 'termtosvg.' + name
            res_class = res_name
            colors[name] = res_db.get(res_name, res_class, None)

        palette = ':'.join(colors['color{}'.format(i)]
                           if colors['color{}'.format(i)] is not None else ''
                           for i in range(len(colors) - 2))
        theme = AsciiCastTheme(fg=colors['foreground'],
                               bg=colors['background'],
                               palette=palette)
        return theme

    @staticmethod
    def is_color(color):
        if type(color) == str and len(color) == 7 and color[0] == '#':
            try:
                int(color[1:], 16)
            except ValueError:
                return False
            return True
        return False


_AsciiCastHeader = namedtuple('AsciiCastHeader', ['version', 'width', 'height', 'theme'])


class AsciiCastHeader(AsciiCastRecord, _AsciiCastHeader):
    """Header record

    version: Version of the asciicast file format
    width: Initial number of columns of the terminal
    height: Initial number of lines of the terminal
    theme: Color theme of the terminal
    """
    types = {
        'version': {int},
        'width': {int},
        'height': {int},
        'theme': {type(None), AsciiCastTheme},
    }

    def __new__(cls, version, width, height, theme):
        self = super(AsciiCastHeader, cls).__new__(cls, version, width, height, theme)
        for attr in AsciiCastHeader._fields:
            type_attr = type(self.__getattribute__(attr))
            if type_attr not in cls.types[attr]:
                raise TypeError('Invalid type for attribute {}: {} '.format(attr, type_attr) +
                                '(possible type: {})'.format(cls.types[attr]))

        if version != 2:
            raise ValueError('Only asciicast v2 format is supported')
        return self

    def to_json_line(self):
        attributes = self._asdict()
        if self.theme is not None:
            attributes['theme'] = self.theme._asdict()
        else:
            del attributes['theme']

        return json.dumps(attributes, ensure_ascii=False)

    @classmethod
    def from_json_line(cls, line):
        attributes = json.loads(line)
        filtered_attributes = {attr: attributes[attr] if attr in attributes else None
                               for attr in AsciiCastHeader._fields}
        if filtered_attributes['theme'] is not None:
            filtered_attributes['theme'] = AsciiCastTheme(**filtered_attributes['theme'])
        return cls(**filtered_attributes)


_AsciiCastEvent = namedtuple('AsciiCastEvent', ['time', 'event_type', 'event_data', 'duration'])


class AsciiCastEvent(AsciiCastRecord, _AsciiCastEvent):
    """Event record

    time: Time elapsed since the beginning of the recording in seconds
    event_type: Type 'o' if the data was captured on the standard output of the terminal, type
                'i' if it was captured on the standard input
    event_data: Data captured during the recording
    duration: Duration of the event in seconds (non standard field)
    """
    types = {
        'time': {int, float},
        'event_type': {str},
        'event_data': {bytes},
        'duration': {type(None), int, float},
    }

    def __new__(cls, *args, **kwargs):
        self = super(AsciiCastEvent, cls).__new__(cls, *args, **kwargs)
        for attr in AsciiCastEvent._fields:
            type_attr = type(self.__getattribute__(attr))
            if type_attr not in cls.types[attr]:
                raise TypeError('Invalid type for attribute {}: {} '.format(attr, type_attr) +
                                '(possible type: {})'.format(cls.types[attr]))
        return self

    def to_json_line(self):
        event_data = utf8_decoder.decode(self.event_data)
        attributes = [self.time, self.event_type, event_data]
        return json.dumps(attributes, ensure_ascii=False)

    @classmethod
    def from_json_line(cls, line):
        attributes = json.loads(line)
        time, event_type, event_data = attributes
        event_data = event_data.encode('utf-8')
        return cls(time, event_type, event_data, None)

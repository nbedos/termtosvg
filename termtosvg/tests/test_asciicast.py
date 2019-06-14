import unittest

from termtosvg.asciicast import AsciiCastV2Header, AsciiCastV2Event, AsciiCastV2Record, \
                                AsciiCastV2Theme, AsciiCastError, _read_v1_records


class TestAsciicast(unittest.TestCase):
    def test_AsciiCastV2Theme(self):
        def palette(n):
            return ':'.join(['#000000'] * n)

        failure_test_cases = [
            ('invalid foreground color', None, '#ABCDEF', palette(8)),
            ('invalid hex number', '#BCDEFG', '#ABCDEF', palette(8)),
            ('invalid foreground color', '#123456', None, palette(16)),
            ('invalid palette', '#123456', '#XXXXXX', None),
            ('incomplete palette', '#123456', '#ABCDEF', palette(7)),
        ]
        for case, fg, bg, colors in failure_test_cases:
            with self.subTest(case=case):
                with self.assertRaises(AsciiCastError):
                    AsciiCastV2Theme(fg, bg, colors)

    cast_v2_lines = [
        # Header: Missing theme
        '{"version": 2, "width": 212, "height": 53}',
        # Header: 8 color theme
        '{"version": 2, "width": 212, "height": 53, "theme": {"fg": "#000000", "bg": "#AAAAAA", "palette": "#000000:#111111:#222222:#333333:#444444:#555555:#666666:#777777"}}',
        # Header: 16 color theme
        '{"version": 2, "width": 212, "height": 53, "theme": {"fg": "#000000", "bg": "#AAAAAA", "palette": "#000000:#111111:#222222:#333333:#444444:#555555:#666666:#777777:#888888:#999999:#AAAAAA:#bbbbbb:#CCCCCC:#DDDDDD:#EEEEEE:#ffffff"}}',
        # Header: additional values
        '{"version": 2, "width": 212, "height": 53, "timestamp": 123456798123}',
        # Header: idle_time_limit
        '{"version": 2, "width": 212, "height": 53, "timestamp": 123456798123, "idle_time_limit": 42}',
        # Float idle time limit (https://github.com/nbedos/termtosvg/issues/97)
        '{"version": 2, "width": 212, "height": 53, "idle_time_limit": 1.234}',
        # Event: Non printable characters
        '[0.010303, "o", "\\u001b[1;31mnico \\u001b[0;34m~\\u001b[0m"]',
        # Event: Unicode characters
        '[1.146397, "o", "❤ ☀ ☆ ☂ ☻ ♞ ☯ ☭ ☢ € →"]',
        # Event: time is an integer and not a float
        '[2, "o", "\\r\\n"]',
    ]

    color_theme_8 = AsciiCastV2Theme(fg='#000000', bg='#AAAAAA', palette='#000000:#111111:'
                                     '#222222:#333333:#444444:#555555:#666666:#777777')
    color_theme_16 = AsciiCastV2Theme(fg='#000000', bg='#AAAAAA', palette='#000000:#111111:'
                                      '#222222:#333333:#444444:#555555:#666666:#777777:#888888:'
                                      '#999999:#AAAAAA:#bbbbbb:#CCCCCC:#DDDDDD:#EEEEEE:#ffffff')
    cast_v2_events = [
        AsciiCastV2Header(2, 212, 53, None),
        AsciiCastV2Header(2, 212, 53, color_theme_8),
        AsciiCastV2Header(2, 212, 53, color_theme_16),
        AsciiCastV2Header(2, 212, 53, None),
        AsciiCastV2Header(2, 212, 53, None, 42),
        AsciiCastV2Header(2, 212, 53, None, 1.234),
        AsciiCastV2Event(0.010303, 'o', '\u001b[1;31mnico \u001b[0;34m~\u001b[0m', None),
        AsciiCastV2Event(1.146397, 'o', '❤ ☀ ☆ ☂ ☻ ♞ ☯ ☭ ☢ € →', None),
        AsciiCastV2Event(2, 'o', '\r\n', None),
    ]

    def test_from_json(self):
        test_cases = zip(TestAsciicast.cast_v2_lines, TestAsciicast.cast_v2_events)
        for index, (line, event) in enumerate(test_cases):
            with self.subTest(case='line #{}'.format(index)):
                self.assertEqual(event, AsciiCastV2Record.from_json_line(line))

        failure_test_cases = [
            ('header v2: invalid version', '{"version": "x", "width": 212, "height": 53}'),
            ('header v2: invalid width', '{"version": 2, "width": "x", "height": 53}'),
            ('header v2: invalid height', '{"version": 2, "width": "212", "height": null}'),
            ('header v2: wrong number of attributes', '{"version": 2}'),
            ('event v2: invalid time', '["x", "o", "ls"]'),
            ('event v2: invalid event_type', '[2.0, 123, "ls"]'),
            ('event v2: invalid event_data', '[2.0, 123, 42]'),
            ('event v2: invalid number of attributes', '[2.0, 123, "ls", "ls"]'),
            ('invalid record', '{"aaa": 42}'),
        ]
        for case, line in failure_test_cases:
            with self.subTest(case=case):
                with self.assertRaises(AsciiCastError):
                    AsciiCastV2Record.from_json_line(line)

    def test_to_json(self):
        test_cases = zip(TestAsciicast.cast_v2_lines, TestAsciicast.cast_v2_events)
        for index, (line, event) in enumerate(test_cases):
            # extra value test case only useful for from_json
            if 'timestamp' in line:
                continue
            with self.subTest(case='record #{}'.format(index)):
                self.assertEqual(event.to_json_line(), line)

    cast_v1_lines = '\r\n'.join(['{',
                                 '  "version": 1,',
                                 '  "width": 212,',
                                 '  "height": 53,',
                                 '  "duration": 2,',
                                 '  "command": "/bin/bash",',
                                 '  "title": "",',
                                 '  "env": {},',
                                 '  "stdout": [',
                                 '    [0.010303, "\\u001b[1;31mnico \\u001b[0;34m~\\u001b[0m"],',
                                 '    [1.136094, "❤ ☀ ☆ ☂ ☻ ♞ ☯ ☭ ☢ € →"],',
                                 '    [0.853603, "\\r\\n"]',
                                 '  ]',
                                 '}'])

    cast_v1_events = [
        AsciiCastV2Header(2, 212, 53, None),
        AsciiCastV2Event(0.010303, 'o', '\u001b[1;31mnico \u001b[0;34m~\u001b[0m',
                         None),
        AsciiCastV2Event(1.146397, 'o', '❤ ☀ ☆ ☂ ☻ ♞ ☯ ☭ ☢ € →', None),
        AsciiCastV2Event(2, 'o', '\r\n', None),
    ]

    def test__read_v1_records(self):
        test_cases = zip(TestAsciicast.cast_v1_lines,
                         TestAsciicast.cast_v1_events,
                         _read_v1_records(TestAsciicast.cast_v1_lines))
        for index, (line, expected_event, event) in enumerate(test_cases):
            with self.subTest(case='record #{}'.format(index)):
                if isinstance(event, AsciiCastV2Header):
                    self.assertEqual(event, expected_event)
                elif isinstance(event, AsciiCastV2Event):
                    self.assertAlmostEqual(event.time, expected_event.time, delta=10e-10)
                    self.assertEqual(event.event_data, expected_event.event_data)
                    self.assertEqual(event.event_type, expected_event.event_type)
                    self.assertEqual(event.duration, expected_event.duration)

        failure_test_cases = [
            ('invalid version', '{"version": null, "width": 212, "height": 53, "duration": 2, "stdout": []}'),
            ('invalid width', '{"version": 1, "width": null, "height": 53, "duration": 2, "stdout": []}'),
            ('invalid height', '{"version": 1, "width": 212, "height": "xx", "duration": 2, "stdout": []}'),
            ('invalid stdout', '{"version": 1, "width": 212, "height": 53, "duration": 2, "stdout": 42}'),
            ('missing version', '{"width": 212, "height": 53, "duration": 2, "stdout": []}'),
            ('missing height', '{"version": 1, "width": 212, "duration": 2, "stdout": []}'),
            ('invalid event', '{"version": 1, "width": 212, "height": 53, "duration": 2, "stdout": [[]]}'),
            ('invalid event', '{"version": 1, "width": 212, "height": 53, "duration": 2, "stdout": [[0]]}'),
            ('invalid event', '{"version": 1, "width": 212, "height": 53, "duration": 2, "stdout": [[0, "a", 2]]}'),
            ('invalid event duration', '{"version": 1, "width": 212, "height": 53, "duration": 2, "stdout": [["aaa", "a"]]}'),
            ('invalid JSON (header)','#####'),
            ('invalid JSON (event)', '{"version": 1, "width": 212, "height": 53, "duration": 2, "stdout": [[###]}'),
        ]

        for case, data in failure_test_cases:
            with self.subTest(case=case):
                with self.assertRaises(AsciiCastError):
                    for _ in _read_v1_records(data):
                        pass

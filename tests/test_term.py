import os
import unittest

from vectty import term

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
    def test__record(self):
        commands = ['echo $SHELL && sleep 0.1;',
                    'tree && 0.1;',
                    'ls && sleep 0.1;',
                    'whoami && sleep 0.1;',
                    'exit;',
                    '']

        # Use pipes in lieu of stdin and stdout
        fd_in_read, fd_in_write = os.pipe()
        fd_out_read, fd_out_write = os.pipe()

        session = term.TerminalSession()
        session.lines = 24
        session.columns = 80

        os.write(fd_in_write, '\r\n'.join(commands).encode('utf-8'))
        for item in session._record(input_fileno=fd_in_read, output_fileno=fd_out_write):
            pass

        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test_replay(self):
        nbr_records = 5
        timings = [{'time': i, 'event-type': 'o', 'event-data': f'{i}\r\n'.encode('utf-8')}
                   for i in range(nbr_records)]

        session = term.TerminalSession()
        session.lines = 24
        session.columns = 80

        lines = (line for line in session.replay(timings, 0.05) if line[1])
        for i, line in enumerate(lines):
            self.assertEqual(line[1][0].value, str(i))

    def test__parse_xresources(self):
        with self.subTest(case='All valid colors'):
            color_mapping = term.TerminalSession._parse_xresources(xresources_valid)
            for i in range(16):
                self.assertIn(f'color{i}', color_mapping)
            self.assertEqual(color_mapping['background'], '#002b36')
            self.assertEqual(color_mapping['foreground'], '#839496')

        # Should succeed even though colors are missing
        with self.subTest(case='Not all colors defined'):
            term.TerminalSession._parse_xresources(xresources_incomplete)

        with self.subTest(case='Empty Xresource'):
            term.TerminalSession._parse_xresources(xresources_empty)

    def test__get_xresources(self):
        term.TerminalSession._get_xresources()

    def test_get_configuration(self):
        session = term.TerminalSession()
        session.get_configuration()

    def test__group_by_time(self):
        timings = [
            {'version': 2, 'width': 80, 'height': 24},
            {'time': 0.00, 'event-type': 'o', 'event-data': b'1'},
            {'time': 0.50, 'event-type': 'o', 'event-data': b'2'},
            {'time': 0.80, 'event-type': 'o', 'event-data': b'3'},
            {'time': 2.00, 'event-type': 'o', 'event-data': b'4'},
            {'time': 2.10, 'event-type': 'o', 'event-data': b'5'},
            {'time': 3.00, 'event-type': 'o', 'event-data': b'6'},
            {'time': 3.10, 'event-type': 'o', 'event-data': b'7'},
            {'time': 3.20, 'event-type': 'o', 'event-data': b'8'},
            {'time': 3.30, 'event-type': 'o', 'event-data': b'9'}
        ]

        expected_timings = [
            {'version': 2, 'width': 80, 'height': 24},
            {'time': 0.00, 'event-type': 'o', 'event-data': b'1', 'duration': 0.50},
            {'time': 0.50, 'event-type': 'o', 'event-data': b'23', 'duration': 1.50},
            {'time': 2.00, 'event-type': 'o', 'event-data': b'45', 'duration': 1.00},
            {'time': 3.00, 'event-type': 'o', 'event-data': b'6789', 'duration': 1.234}
        ]

        result = list(term.TerminalSession._group_by_time(timings, 0.5, 1.234))
        self.assertEqual(len(expected_timings), len(result))

        for expected_record, record in zip(expected_timings, result):
            self.assertEqual(expected_record.keys(), record.keys())
            for key in expected_record:
                if type(expected_record[key]) == float:
                    self.assertAlmostEqual(expected_record[key], record[key], 0.001)
                else:
                    self.assertEqual(expected_record[key], record[key])


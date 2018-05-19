import datetime
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

        session = term.TerminalSession()

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

        session = term.TerminalSession()
        for buffer in session.replay(timings):
            pass

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
        def delta_ms(n):
            return datetime.timedelta(milliseconds=n)
        
        timings = [(b' ', 0), (b'$', 0), (b' ', 0), (b'c', 60), (b'm', 120), (b'd', 180),
                   (b'\r', 260), (b'\n', 260), (b' ', 260), (b'$', 260), (b' ', 260)]

        now = datetime.datetime.now()
        real_timings = [(bs, now + delta_ms(n)) for bs, n in timings]
        result = term.TerminalSession._group_by_time(timings=real_timings,
                                                     min_frame_duration=50,
                                                     last_frame_duration=1234)

        expected_result = [(b' $ ', delta_ms(60)),
                           (b'c', delta_ms(60)),
                           (b'm', delta_ms(60)),
                           (b'd', delta_ms(80)),
                           (b'\r\n $ ', delta_ms(1234))]
        self.assertEqual(expected_result, list(result))

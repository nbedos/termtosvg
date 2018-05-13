from collections import defaultdict
from contextlib import contextmanager
import datetime
import logging
import os
import pyte.screens
import sys
import unittest

from src import svg

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


data = 'Script started on 2018-05-05 16:56:18+02:00\n' \
       '\x1b_user@arch:/tmp\x1b\\\x1b[91muser \x1b[34m/tmp\x1b[91m $ \x1b[0mecho "aaa"\n' \
       'aaa\n\x1b_user@arch:/tmp\x1b\\\x1b[91muser \x1b[34m/tmp\x1b[91m $ \x1b[0mecho "bbb"\n' \
       'bbb\n\x1b_user@arch:/tmp\x1b\\\x1b[91muser \x1b[34m/tmp\x1b[91m $ \x1b[0mexit\n\n' \
       'Script done on 2018-05-05 16:56:27+02:00\n'


@contextmanager
def pipe_fds():
    fd_read, fd_write = os.pipe()
    yield (fd_read, fd_write)
    os.close(fd_read)
    os.close(fd_write)


class TestTerminalSession(unittest.TestCase):
    def test_record(self):
        commands = '\r\n'.join(['echo $SHELL && sleep 0.1;',
                                'tree && 0.1;',
                                'ls && sleep 0.1;',
                                'whoami && sleep 0.1;',
                                'exit;',
                                ''])
        # stdin is replaced by the reading end of the pipe, so that
        # we can feed it commands to be executed by the shell from the writing end
        with pipe_fds() as (fdr, fdw):
            os.dup2(fdr, sys.stdin.fileno())
            os.write(fdw, commands.encode('utf-8'))
            session = svg.TerminalSession()
            for _ in session.record():
                pass

    def test_group_by_time(self):
        timings = [(b' ', 0), (b'$', 0), (b' ', 0), (b'c', 60), (b'm', 120), (b'd', 180),
                   (b'\r', 260), (b'\n', 260), (b' ', 260), (b'$', 260), (b' ', 260)]

        now = datetime.datetime.now()
        threshold = datetime.timedelta(milliseconds=50)
        real_timings = [(bs, now + datetime.timedelta(milliseconds=n)) for bs, n in timings]
        result = svg.group_by_time(real_timings, threshold=threshold)

        expected_result = [(b' $ ', now),
                           (b'c', now + datetime.timedelta(milliseconds=60)),
                           (b'm', now + datetime.timedelta(milliseconds=120)),
                           (b'd', now + datetime.timedelta(milliseconds=180)),
                           (b'\r\n $ ', now + datetime.timedelta(milliseconds=260))]
        self.assertEqual(expected_result, result)

    def test_ansi_color_to_xml(self):
        with self.subTest(case='Named color'):
            self.assertEqual('black', svg.ansi_color_to_xml('black'))

        with self.subTest(case='Valid hexadecimal color'):
            self.assertEqual('#000000', svg.ansi_color_to_xml('000000'))
            self.assertEqual('#123456', svg.ansi_color_to_xml('123456'))
            self.assertEqual('#ABCDEF', svg.ansi_color_to_xml('abcdef').upper())
            self.assertEqual('#FFFFFF', svg.ansi_color_to_xml('ffffff').upper())

        with self.subTest(case='Invalid hexadecimal color'):
            with self.assertRaises(ValueError):
                svg.ansi_color_to_xml('00000z')

            with self.assertRaises(ValueError):
                svg.ansi_color_to_xml('12345')

    def test_render_animation(self):
        pass

    # def test_link_cells(self):
    #     matrix_size = 10
    #
    #     matrix = defaultdict(dict)
    #     # Mapping between a value found in the matrix and the sets of adjacent cells containing this
    #     # value
    #     expected = {
    #         0: {
    #             frozenset({(0, j) for j in range(matrix_size)})
    #         },
    #         1: {
    #             frozenset({(i, 0) for i in range(1, matrix_size)}),
    #             frozenset({(6, 6), (6, 7), (6, 8), (7, 8), (8, 8), (8, 7), (8, 6), (7, 6)})
    #         },
    #         2: {
    #             frozenset({(1, 1), (1, 2), (2, 2)}),
    #             frozenset({(4, 4), (5, 4), (5, 5)})
    #         }
    #     }
    #
    #     for value in expected:
    #         for cells in expected[value]:
    #             for (i, j) in cells:
    #                 assert i not in matrix or j not in matrix[i]
    #                 matrix[i][j] = value
    #
    #     self.assertEqual(svg.link_cells(matrix), expected)

    def test_draw_bg(self):
        def mock_char(bg):
            return pyte.screens.Char(' ', bg=bg, reverse=False)

        buffer = defaultdict(dict)
        buffer_size = 4

        with self.subTest(case='Single color buffer'):
            for i in range(buffer_size):
                for j in range(buffer_size):
                    buffer[i][j] = mock_char('black')
            svg.draw_bg(buffer, 10, 'test_bg').tostring()

    def test_get_Xresources_colors(self):
        print(svg.get_Xresources_colors())

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
        print(svg.serialize_css_dict(css))

    def test_draw_fg(self):
        pass

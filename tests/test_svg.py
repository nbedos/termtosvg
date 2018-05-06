from contextlib import contextmanager
import datetime
import unittest
import os
import sys

from src import svg

data = 'Script started on 2018-05-05 16:56:18+02:00\n' \
       '\x1b_nico@arch:/tmp\x1b\\\x1b[91mnico \x1b[34m/tmp\x1b[91m $ \x1b[0mecho "aaa"\n' \
       'aaa\n\x1b_nico@arch:/tmp\x1b\\\x1b[91mnico \x1b[34m/tmp\x1b[91m $ \x1b[0mecho "bbb"\n' \
       'bbb\n\x1b_nico@arch:/tmp\x1b\\\x1b[91mnico \x1b[34m/tmp\x1b[91m $ \x1b[0mexit\n\n' \
       'Script done on 2018-05-05 16:56:27+02:00\n'


@contextmanager
def pipe_fds():
    fd_read, fd_write = os.pipe()
    yield (fd_read, fd_write)
    os.close(fd_read)
    os.close(fd_write)


class TestSVG(unittest.TestCase):
    def test_record(self):
        commands = '\r\n'.join(['echo $SHELL;',
                                'tree;',
                                'ls;',
                                'whoami;',
                                'exit;',
                                ''])
        # stdin is replaced by the reading end of the pipe, so that
        # we can feed it commands to be executed by the shell from the writing end
        with pipe_fds() as (fdr, fdw):
            os.dup2(fdr, sys.stdin.fileno())
            os.write(fdw, commands.encode('utf-8'))
            records, timings = svg.record()

    def test_convert(self):
        with self.subTest(case='data'):
            converted = svg.convert(data)
            unprintable_chars = [c for c in converted if not c.isprintable() and c != '\n']
            self.assertFalse(unprintable_chars)

    def test_draw(self):
        text = 'nico /tmp $ echo "aaa"\n' \
               'aaa\n' \
               'nico /tmp $ echo "bbb"\n' \
               'bbb\n' \
               'nico /tmp $ exit\n'
        now = datetime.datetime.now()
        timings = [
            [
                (b'nico /tmp $ ', now),
                (b'e', now + datetime.timedelta(milliseconds=90)),
                (b'c', now + datetime.timedelta(milliseconds=90*2)),
                (b'h', now + datetime.timedelta(milliseconds=90*3)),
                (b'o', now + datetime.timedelta(milliseconds=90*4)),
                (b' ', now + datetime.timedelta(milliseconds=90*5)),
                (b'"', now + datetime.timedelta(milliseconds=90*6)),
                (b'a', now + datetime.timedelta(milliseconds=90*7)),
                (b'a', now + datetime.timedelta(milliseconds=90*8)),
                (b'a', now + datetime.timedelta(milliseconds=90*9)),
                (b'"', now + datetime.timedelta(milliseconds=90*10))
            ],
            [
                (b'aaa', now + datetime.timedelta(milliseconds=90*11))
            ],
            [
                (b'nico /tmp $ ', now + datetime.timedelta(milliseconds=90*21)),
                (b'e', now + datetime.timedelta(milliseconds=90 * 22)),
                (b'c', now + datetime.timedelta(milliseconds=90 * 23)),
                (b'h', now + datetime.timedelta(milliseconds=90 * 24)),
                (b'o', now + datetime.timedelta(milliseconds=90 * 25)),
                (b' ', now + datetime.timedelta(milliseconds=90 * 26)),
                (b'"', now + datetime.timedelta(milliseconds=90 * 27)),
                (b'b', now + datetime.timedelta(milliseconds=90 * 28)),
                (b'b', now + datetime.timedelta(milliseconds=90 * 29)),
                (b'b', now + datetime.timedelta(milliseconds=90 * 30)),
                (b'"', now + datetime.timedelta(milliseconds=90 * 31))
            ],
            [
                (b'bbb', now + datetime.timedelta(milliseconds=90 * 32))
            ]
        ]
        svg.draw(timings, '/tmp/draw.svg')

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

    def test_group_by_line(self):
        timings = [(b'prompt $ ', 0),
                   (b' ls -l\n', 1),
                   (b'prompt $ ', 2),
                   (b'l', 3),
                   (b's', 4),
                   (b'\n', 5),
                   (b'prompt $ ls\n', 6)]

        expected_result = [
            [(b'prompt $ ', 0), (b' ls -l', 1)],
            [(b'prompt $ ', 2), (b'l', 3), (b's', 4)],
            [(b'prompt $ ls', 6)]
        ]

        result = svg.group_by_line(timings)
        self.assertEqual(expected_result, result)
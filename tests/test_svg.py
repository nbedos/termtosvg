from contextlib import contextmanager
import datetime
import unittest
import os
import sys
import svgwrite

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
            timings = svg.record()
            squashed_timings = svg.group_by_time(timings)
            svg.render_animation(squashed_timings, '/tmp/test.svg')

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
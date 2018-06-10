import os
import time
import unittest

from unittest.mock import Mock
from Xlib.error import DisplayError

import termtosvg.__main__ as __main__

SHELL_COMMANDS = [
    'echo $SHELL && sleep 0.1;\r\n',
    'tree && 0.1;\r\n',
    'ls && sleep 0.1;\r\n',
    'w',
    'h',
    'o',
    'a',
    'm',
    'i\r\n',
    'exit;\r\n'
]


class TestMain(unittest.TestCase):
    @staticmethod
    def run_main(shell_commands, args):
        # Use pipes in lieu of stdin and stdout
        fd_in_read, fd_in_write = os.pipe()
        fd_out_read, fd_out_write = os.pipe()

        pid = os.fork()
        if pid == 0:
            # Child process
            for line in shell_commands:
                os.write(fd_in_write, line.encode('utf-8'))
                time.sleep(0.060)
            os._exit(0)

        __main__.main(fd_in_read, fd_out_write, args)

        os.waitpid(pid, 0)
        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test_main(self):
        with self.subTest(case='provided theme'):
            args = ['termtosvg', '-v', '--theme', 'solarized-light']
            TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='fallback theme'):
            # Force use of fallback theme by mocking _get_x_resources
            get_x_mock = Mock(side_effect=DisplayError(None))
            with unittest.mock.patch('termtosvg.term._get_xresources', get_x_mock):
                args = ['termtosvg']
                TestMain.run_main(SHELL_COMMANDS, args)

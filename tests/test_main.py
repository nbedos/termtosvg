import os
import tempfile
import time
import unittest

import termtosvg.main

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
    'echo -e "\\033[1;31mbright red fg\\033[0m"\r\n',
    'echo -e "\\033[1;41mbright red bg\\033[0m"\r\n',
    'echo -e "\\033[1mbold\\033[0m"\r\n',
    'echo -e "\\033[3mitalics\\033[0m"\r\n',
    'echo -e "\\033[4munderscore\\033[0m"\r\n',
    'exit;\r\n'
]


class TestMain(unittest.TestCase):
    test_cases = [
        [],
        ['--verbose'],
        ['--screen-geometry', '82x19'],
        ['-g', '82x19'],
        ['--template', 'plain'],
        ['-t', 'plain'],
        ['--verbose', '--screen-geometry', '82x19', '--template', 'plain'],
        ['output_filename', '--verbose', '--screen-geometry', '82x19', '--template', 'plain'],
        ['--verbose', '--screen-geometry', '82x19', '--template', 'plain', 'output_filename'],
        ['-v', '-g', '82x19', '-t', 'plain'],
        ['record'],
        ['record', 'output_filename'],
        ['record', 'output_filename', '--verbose', '--screen-geometry', '82x19'],
        ['record', '--verbose', '--screen-geometry', '82x19'],
        ['render', 'input_filename'],
        ['render', 'input_filename', '--verbose'],
        ['render', 'input_filename', '--verbose', '--template', 'plain'],
        ['render', 'input_filename', 'output_filename'],
        ['render', 'input_filename', 'output_filename', '--verbose'],
        ['render', 'input_filename', 'output_filename', '--verbose', '--template', 'plain'],
    ]

    def test_parse(self):
        for args in self.test_cases:
            with self.subTest(case=args):
                cmd, parsed_args = termtosvg.main.parse(args, {'plain': b''}, 'plain', '48x95')

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

        termtosvg.main.main(args, fd_in_read, fd_out_write)

        os.waitpid(pid, 0)
        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test_main(self):
        _, cast_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.cast')
        svg_filename = cast_filename[:-5] + '.svg'

        with self.subTest(case='record (no filename)'):
            args = ['termtosvg', 'record']
            TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='record (with filename)'):
            args = ['termtosvg', 'record', cast_filename]
            TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='record (with geometry)'):
            args = ['termtosvg', 'record', '--screen-geometry', '82x19']
            TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='render (no output filename)'):
            args = ['termtosvg', 'render', cast_filename]
            TestMain.run_main([], args)

        with self.subTest(case='render (with output filename)'):
            args = ['termtosvg', 'render', cast_filename, svg_filename]
            TestMain.run_main([], args)

        with self.subTest(case='render (with geometry)'):
            args = ['termtosvg', 'render', cast_filename]
            TestMain.run_main([], args)

        with self.subTest(case='render (with template)'):
            args = ['termtosvg', 'render', cast_filename, '--template', 'WINDOW_frame']
            TestMain.run_main([], args)

        with self.subTest(case='record and render on the fly (fallback theme)'):
            args = ['termtosvg', '--verbose', '--screen-geometry', '82x19']
            TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='record and render on the fly (window_frame template)'):
            args = ['termtosvg', svg_filename, '--template', 'WINDOW_frame', '--verbose']
            TestMain.run_main(SHELL_COMMANDS, args)

        cast_v1_data = '\r\n'.join(['{',
                                    '  "version": 1,',
                                    '  "width": 80,',
                                    '  "height": 32,',
                                    '  "duration": 10,',
                                    '  "command": "/bin/zsh",',
                                    '  "title": "",',
                                    '  "env": {},',
                                    '  "stdout": [',
                                    '    [0.010303, "\\u001b[1;31mnico \\u001b[0;34m~\\u001b[0m"],',
                                    '    [1.136094, "❤ ☀ ☆ ☂ ☻ ♞ ☯ ☭ ☢ € →"],',
                                    '    [0.853603, "\\r\\n"]',
                                    '  ]',
                                    '}'])

        with self.subTest(case='render v1 cast file'):
            _, cast_filename_v1 = tempfile.mkstemp(prefix='termtosvg_', suffix='.cast')
            with open(cast_filename_v1, 'w') as cast_file:
                cast_file.write(cast_v1_data)

            args = ['termtosvg', 'render', cast_filename_v1, svg_filename]
            TestMain.run_main([], args)

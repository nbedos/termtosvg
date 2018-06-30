import os
import tempfile
import time
import unittest

from unittest.mock import Mock
from Xlib.error import DisplayError

import termtosvg.__main__ as __main__
import termtosvg.term as term
from tests.test_term import xresources_minimal

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
    "\033[1;31mbright red fg\033[0m\r\n",
    "\033[1;41mbright red bg\033[0m\r\n",
    'exit;\r\n'
]


# TODO: Replace os.pipe + fork by Popen ?
class TestMain(unittest.TestCase):
    def test_parse(self):
        test_cases = [
            [],
            ['--theme', 'solarized-light'],
            ['--verbose'],
            ['--theme', 'solarized-light', '--verbose'],
            ['--theme', 'solarized-light'],
            ['record'],
            ['record', 'output_filename'],
            ['record', 'output_filename', '--verbose'],
            ['record', '--verbose'],
            ['render', 'input_filename'],
            ['render', 'input_filename', '--verbose'],
            ['render', 'input_filename', '--verbose', '--theme', 'solarized-light'],
            ['render', 'input_filename', '--theme', 'solarized-light'],
            ['render', 'input_filename', 'output_filename'],
            ['render', 'input_filename', 'output_filename', '--verbose'],
            ['render', 'input_filename', 'output_filename', '--verbose', '--theme', 'solarized-light'],
            ['render', 'input_filename', 'output_filename', '--theme', 'solarized-light'],
        ]

        for args in test_cases:
            with self.subTest(case=args):
                __main__.parse(args)

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

        __main__.main(args, fd_in_read, fd_out_write)

        os.waitpid(pid, 0)
        for fd in fd_in_read, fd_in_write, fd_out_read, fd_out_write:
            os.close(fd)

    def test_main(self):
        _, cast_filename = tempfile.mkstemp(prefix='termtosvg_', suffix='.cast')
        svg_filename = cast_filename[:-5] + '.svg'

        with self.subTest(case='record (no filename)'):
            # Force use of fallback theme by mocking _get_x_resources
            get_x_mock = Mock(side_effect=DisplayError(None))
            with unittest.mock.patch('termtosvg.term._get_xresources', get_x_mock):
                args = ['termtosvg', 'record']
                TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='record (with filename)'):
            # Force use of fallback theme by mocking _get_x_resources
            get_x_mock = Mock(side_effect=DisplayError(None))
            with unittest.mock.patch('termtosvg.term._get_xresources', get_x_mock):
                args = ['termtosvg', 'record', cast_filename]
                TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='render (no filename)'):
            args = ['termtosvg', 'render', cast_filename]
            TestMain.run_main([], args)

        with self.subTest(case='render (with filename)'):
            args = ['termtosvg', 'render', cast_filename, svg_filename]
            TestMain.run_main([], args)

        with self.subTest(case='render (with theme)'):
            args = ['termtosvg', 'render', cast_filename, '--theme', 'circus']
            TestMain.run_main([], args)

        with self.subTest(case='record and render on the fly (fallback theme)'):
            # Force use of fallback theme by mocking _get_x_resources]
            get_x_mock = Mock(side_effect=DisplayError(None))
            with unittest.mock.patch('termtosvg.term._get_xresources', get_x_mock):
                args = ['termtosvg', '--verbose']
                TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='record and render on the fly (system theme)'):
            # Mock color info gathering
            xresources_dracula = term.default_themes()['dracula']
            get_x_mock = Mock(return_value=xresources_dracula)
            with unittest.mock.patch('termtosvg.term._get_xresources', get_x_mock):
                args = ['termtosvg', '--verbose', svg_filename]
                TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='record and render on the fly (system theme)'):
            # Mock color info gathering
            xresources_dracula = term.default_themes()['dracula']
            get_x_mock = Mock(return_value=xresources_dracula)
            with unittest.mock.patch('termtosvg.term._get_xresources', get_x_mock):
                args = ['termtosvg', svg_filename, '--theme', 'circus', '--verbose']
                TestMain.run_main(SHELL_COMMANDS, args)

        with self.subTest(case='8 color palette'):
            # Mock color info gathering
            get_x_mock = Mock(return_value=xresources_minimal)
            with unittest.mock.patch('termtosvg.term._get_xresources', get_x_mock):
                args = ['termtosvg', svg_filename]
                TestMain.run_main(SHELL_COMMANDS, args)


MINIMAL_CONFIG = """[GLOBAL]
theme=dark
font=Deja Vu Sans Mono
[dark]
foreground=#FFFFFF
background=#000000
color0=#000000
color1=#111111
color2=#222222
color3=#333333
color4=#444444
color5=#555555
color6=#666666
color7=#777777
"""

NO_GLOBAL_SECTION_CONFIG = MINIMAL_CONFIG.replace('[GLOBAL]', ';[GLOBAL]')
NO_FONT_CONFIG = MINIMAL_CONFIG.replace('font', ';font')
NO_THEME_CONFIG = MINIMAL_CONFIG.replace('theme', ';theme')
WRONG_THEME_CONFIG = MINIMAL_CONFIG.replace('theme=dark', 'theme=white')
DUPLICATES_CONFIG = MINIMAL_CONFIG.replace('theme=dark',
                                           'font=courrier\r\ntheme=dark\r\ntheme=white\r\n[dark]')


class TestConf(unittest.TestCase):
    def test_parse_config(self):
        with self.subTest(case='minimal config'):
            font, theme = __main__.parse_config(MINIMAL_CONFIG, '')
            self.assertEqual(font, 'Deja Vu Sans Mono')
            self.assertEqual(theme.fg.lower(), '#ffffff')
            self.assertEqual(theme.bg.lower(), '#000000')

        test_cases = [
            ('default config', __main__.DEFAULT_CONFIG, __main__.DEFAULT_CONFIG),
            ('empty user config', '', __main__.DEFAULT_CONFIG),
            ('No global section', NO_GLOBAL_SECTION_CONFIG, __main__.DEFAULT_CONFIG),
            ('No font property', NO_FONT_CONFIG, __main__.DEFAULT_CONFIG),
            ('No theme property', NO_THEME_CONFIG, __main__.DEFAULT_CONFIG),
            ('Invalid theme property', WRONG_THEME_CONFIG, __main__.DEFAULT_CONFIG),
        ]

        for case, user_config, default_config in test_cases:
            with self.subTest(case=case):
                font, theme = __main__.parse_config(user_config, default_config)
                self.assertEqual(font, 'Deja Vu Sans Mono')
                self.assertEqual(theme.fg.lower(), '#93a1a1')
                self.assertEqual(theme.bg.lower(), '#002b36')
                palette = theme.palette.split(':')
                self.assertEqual(palette[0].lower(), '#002b36')
                self.assertEqual(palette[15].lower(), '#fdf6e3')


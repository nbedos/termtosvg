import tempfile
import unittest
from unittest.mock import patch

import termtosvg.config as config


MINIMAL_CONFIG = """[GLOBAL]
theme=dark
font=DejaVu Sans Mono
playpause=false
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
UPPERCASE_CONFIG = MINIMAL_CONFIG.upper()
NO_GLOBAL_SECTION_CONFIG = MINIMAL_CONFIG.replace('[GLOBAL]', ';[GLOBAL]')
NO_FONT_CONFIG = MINIMAL_CONFIG.replace('font', ';font')
NO_THEME_CONFIG = MINIMAL_CONFIG.replace('theme', ';theme')
NO_PP_CONFIG = MINIMAL_CONFIG.replace('playpause', ';playpause')
WRONG_THEME_CONFIG = MINIMAL_CONFIG.replace('theme=dark', 'theme=white')
DUPLICATES_CONFIG = MINIMAL_CONFIG.replace('theme=dark',
                                           'font=courrier\r\ntheme=dark\r\ntheme=white\r\n[dark]')
OVERRIDE_CONFIG = MINIMAL_CONFIG.replace('#000000', '#FFFFFF').replace('DejaVu Sans Mono', 'mono')


class TestConf(unittest.TestCase):
    def test_conf_to_dict(self):
        test_cases = [
            ('Minimal config', MINIMAL_CONFIG),
            ('Uppercase config', UPPERCASE_CONFIG),
        ]
        for case, configuration in test_cases:
            with self.subTest(case=case):
                config_dict = config.conf_to_dict(configuration)
                self.assertEqual(config_dict['GlOBal']['font'].lower(), 'dejavu sans mono')
                self.assertEqual(config_dict['Dark'].fg.lower(), '#ffffff')
                self.assertEqual(config_dict['dark'].bg.lower(), '#000000')

        with self.subTest(case='minimal config'):
            config_dict = config.conf_to_dict(MINIMAL_CONFIG)
            self.assertEqual(config_dict['GLOBAL']['font'], 'DejaVu Sans Mono')
            self.assertEqual(config_dict['dark'].fg.lower(), '#ffffff')
            self.assertEqual(config_dict['dark'].bg.lower(), '#000000')

    def test_get_configuration(self):
        test_cases = [
            ('Default config', config.DEFAULT_CONFIG, config.DEFAULT_CONFIG),
            ('Empty user config', '', config.DEFAULT_CONFIG),
            ('No global section', NO_GLOBAL_SECTION_CONFIG, config.DEFAULT_CONFIG),
            ('No font property', NO_FONT_CONFIG, config.DEFAULT_CONFIG),
            ('No theme property', NO_THEME_CONFIG, config.DEFAULT_CONFIG),
            ('No playpause property', NO_PP_CONFIG, config.DEFAULT_CONFIG),
            ('Invalid theme property', WRONG_THEME_CONFIG, config.DEFAULT_CONFIG),
        ]

        for case, user_config, default_config in test_cases:
            with self.subTest(case=case):
                config_dict = config.get_configuration(user_config, default_config)
                self.assertEqual(config_dict['GLOBAL']['font'], 'DejaVu Sans Mono')
                self.assertEqual(config_dict['solarized-dark'].fg.lower(), '#93a1a1')
                self.assertEqual(config_dict['solarized-dark'].bg.lower(), '#002b36')
                palette = config_dict['solarized-dark'].palette.split(':')
                self.assertEqual(palette[0].lower(), '#002b36')
                self.assertEqual(palette[15].lower(), '#fdf6e3')

        with self.subTest(case="Override defaults"):
            config_dict = config.get_configuration(OVERRIDE_CONFIG, MINIMAL_CONFIG)
            self.assertEqual(config_dict['GLOBAL']['font'], 'mono')
            self.assertEqual(config_dict['dark'].bg.lower(), '#ffffff')
            palette = config_dict['dark'].palette.split(':')
            self.assertEqual(palette[0].lower(), '#ffffff')

    def test_init_read_conf(self):
        with self.subTest(case='XDG_CONFIG_HOME'):
            mock_environ = {
                'XDG_CONFIG_HOME': tempfile.mkdtemp(prefix='termtosvg_config_')
            }
            with patch('os.environ', mock_environ):
                # First call should create config dirs and return it
                self.assertEqual(config.conf_to_dict(config.DEFAULT_CONFIG),
                                 config.init_read_conf())
                # Second call only reads the config file which was created by the first call
                self.assertEqual(config.conf_to_dict(config.DEFAULT_CONFIG),
                                 config.init_read_conf())

        with self.subTest(case='XDG_CONFIG_HOME'):
            mock_environ = {
                'XDG_CONFIG_HOME': tempfile.mkdtemp(prefix='termtosvg_config_')
            }
            with patch('os.environ', mock_environ):
                self.assertEqual(config.conf_to_dict(config.DEFAULT_CONFIG),
                                 config.init_read_conf())

        with self.subTest(case='HOME'):
            mock_environ = {
                'HOME': tempfile.mkdtemp(prefix='termtosvg_config_')
            }
            with patch('os.environ', mock_environ):
                self.assertEqual(config.conf_to_dict(config.DEFAULT_CONFIG),
                                 config.init_read_conf())

        with self.subTest(case='No environment variable'):
            mock_environ = {}
            with patch('os.environ', mock_environ):
                self.assertEqual(config.conf_to_dict(config.DEFAULT_CONFIG),
                                 config.init_read_conf())

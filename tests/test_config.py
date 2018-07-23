import tempfile
import pkgutil
import unittest
from unittest.mock import patch

import termtosvg.config as config


DEFAULT_CONFIG = pkgutil.get_data('termtosvg.config', config.PKG_CONF_PATH).decode('utf-8')
MINIMAL_CONFIG = """[GLOBAL]
theme=dark
font=DejaVu Sans Mono
;screen-geometry=82x19
template=carbon
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
GEOMETRY_CONFIG = MINIMAL_CONFIG.replace(';screen-geometry', 'screen-geometry')
NO_GLOBAL_SECTION_CONFIG = MINIMAL_CONFIG.replace('[GLOBAL]', ';[GLOBAL]')
NO_FONT_CONFIG = MINIMAL_CONFIG.replace('font', ';font')
NO_THEME_CONFIG = MINIMAL_CONFIG.replace('theme', ';theme')
WRONG_THEME_CONFIG = MINIMAL_CONFIG.replace('theme=dark', 'theme=white')
DUPLICATES_CONFIG = MINIMAL_CONFIG.replace('theme=dark',
                                           'font=courrier\r\ntheme=dark\r\ntheme=white\r\n[dark]')
OVERRIDE_CONFIG = (MINIMAL_CONFIG.replace('#000000', '#FFFFFF')
                                 .replace('DejaVu Sans Mono', 'mono')
                                 .replace(';screen-geometry', 'screen-geometry'))


class TestConf(unittest.TestCase):
    def test_conf_to_dict(self):
        test_cases = [
            ('Minimal config', MINIMAL_CONFIG),
            ('Uppercase config', UPPERCASE_CONFIG),
        ]
        for case, configuration in test_cases:
            with self.subTest(case=case):
                config_dict = config.conf_to_dict(configuration)
                self.assertEqual(config_dict['GlOBal']['fOnT'].lower(), 'dejavu sans mono')
                self.assertEqual(config_dict['Dark'].fg.lower(), '#ffffff')
                self.assertEqual(config_dict['dark'].bg.lower(), '#000000')

        with self.subTest(case='minimal config'):
            config_dict = config.conf_to_dict(MINIMAL_CONFIG)
            self.assertEqual(config_dict['GLOBAL']['font'], 'DejaVu Sans Mono')
            self.assertEqual(config_dict['dark'].fg.lower(), '#ffffff')
            self.assertEqual(config_dict['dark'].bg.lower(), '#000000')

        with self.subTest(case='geometry config'):
            config_dict = config.conf_to_dict(GEOMETRY_CONFIG)
            self.assertEqual(config_dict['GLOBAL']['screen-geometry'], (82, 19))

    def test_init_read_conf(self):
        with self.subTest(case='XDG_CONFIG_HOME'):
            mock_environ = {
                'XDG_CONFIG_HOME': tempfile.mkdtemp(prefix='termtosvg_config_')
            }
            with patch('os.environ', mock_environ):
                # First call should create config dirs and return it
                configuration, templates = config.init_read_conf()
                self.assertEqual(config.conf_to_dict(DEFAULT_CONFIG),
                                 configuration)
                # Second call only reads the config file which was created by the first call
                configuration, templates = config.init_read_conf()
                self.assertEqual(config.conf_to_dict(DEFAULT_CONFIG),
                                 configuration)

        with self.subTest(case='XDG_CONFIG_HOME'):
            mock_environ = {
                'XDG_CONFIG_HOME': tempfile.mkdtemp(prefix='termtosvg_config_')
            }
            with patch('os.environ', mock_environ):
                configuration, templates = config.init_read_conf()
                self.assertEqual(config.conf_to_dict(DEFAULT_CONFIG),
                                 configuration)

        with self.subTest(case='HOME'):
            mock_environ = {
                'HOME': tempfile.mkdtemp(prefix='termtosvg_config_')
            }
            with patch('os.environ', mock_environ):
                configuration, templates = config.init_read_conf()
                self.assertEqual(config.conf_to_dict(DEFAULT_CONFIG),
                                 configuration)

        with self.subTest(case='No environment variable'):
            mock_environ = {}
            with patch('os.environ', mock_environ):
                configuration, templates = config.init_read_conf()
                self.assertEqual(config.conf_to_dict(DEFAULT_CONFIG),
                                 configuration)

        with self.subTest(case='Templates'):
            mock_environ = {
                'XDG_CONFIG_HOME': tempfile.mkdtemp(prefix='termtosvg_config_')
            }
            with patch('os.environ', mock_environ):
                # First call to init_read_conf populates directory with default configuration
                default_configuration, default_templates = config.init_read_conf()
                # Second call reads configuration in the directory
                configuration, templates = config.init_read_conf()
                self.assertEqual(default_configuration, configuration)
                self.assertEqual(default_templates, templates)


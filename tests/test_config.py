import unittest

import termtosvg.config as config


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
OVERRIDE_CONFIG = MINIMAL_CONFIG.replace('#000000', '#FFFFFF').replace('Deja Vu Sans Mono', 'mono')


class TestConf(unittest.TestCase):
    def test_conf_to_dict(self):
        with self.subTest(case='minimal config'):
            config_dict = config.conf_to_dict(MINIMAL_CONFIG)
            self.assertEqual(config_dict['GLOBAL']['font'], 'Deja Vu Sans Mono')
            self.assertEqual(config_dict['dark'].fg.lower(), '#ffffff')
            self.assertEqual(config_dict['dark'].bg.lower(), '#000000')

    def test_get_configuration(self):
        test_cases = [
            ('Default config', config.DEFAULT_CONFIG, config.DEFAULT_CONFIG),
            ('Empty user config', '', config.DEFAULT_CONFIG),
            ('No global section', NO_GLOBAL_SECTION_CONFIG, config.DEFAULT_CONFIG),
            ('No font property', NO_FONT_CONFIG, config.DEFAULT_CONFIG),
            ('No theme property', NO_THEME_CONFIG, config.DEFAULT_CONFIG),
            ('Invalid theme property', WRONG_THEME_CONFIG, config.DEFAULT_CONFIG),
        ]

        for case, user_config, default_config in test_cases:
            with self.subTest(case=case):
                config_dict = config.get_configuration(user_config, default_config)
                self.assertEqual(config_dict['GLOBAL']['font'], 'Deja Vu Sans Mono')
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

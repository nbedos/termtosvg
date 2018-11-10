import unittest

import termtosvg.config as config


class TestConf(unittest.TestCase):
    def test_default_tempaltes(self):
        templates = config.default_templates()

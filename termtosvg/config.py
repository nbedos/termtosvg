import configparser
import logging
import os
from typing import Union, Dict

import pkg_resources

import termtosvg.asciicast as asciicast


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

PKG_CONF_PATH = os.path.join('data', 'termtosvg.ini')
DEFAULT_CONFIG = pkg_resources.resource_string(__name__, PKG_CONF_PATH).decode('utf-8')


class CaseInsensitiveDict(dict):
    @classmethod
    def _lower_key(cls, key):
        return key.lower() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        super(CaseInsensitiveDict, self).__init__(*args, **kwargs)
        for key in list(self.keys()):
            value = super(CaseInsensitiveDict, self).pop(key)
            self.__setitem__(key, value)

    def __getitem__(self, key):
        lower_case_key = self.__class__._lower_key(key)
        return super(CaseInsensitiveDict, self).__getitem__(lower_case_key)

    def __setitem__(self, key, value):
        lower_case_key = self.__class__._lower_key(key)
        super(CaseInsensitiveDict, self).__setitem__(lower_case_key, value)

    def __delitem__(self, key):
        lower_case_key = self.__class__._lower_key(key)
        return super(CaseInsensitiveDict, self).__delitem__(lower_case_key)

    def __contains__(self, key):
        lower_case_key = self.__class__._lower_key(key)
        return super(CaseInsensitiveDict, self).__contains__(lower_case_key)

    def pop(self, key, *args, **kwargs):
        lower_case_key = self.__class__._lower_key(key)
        return super(CaseInsensitiveDict, self).pop(lower_case_key, *args, **kwargs)

    def get(self, key, *args, **kwargs):
        lower_case_key = self.__class__._lower_key(key)
        return super(CaseInsensitiveDict, self).get(lower_case_key, *args, **kwargs)

    def setdefault(self, key, *args, **kwargs):
        lower_case_key = self.__class__._lower_key(key)
        return super(CaseInsensitiveDict, self).setdefault(lower_case_key, *args, **kwargs)

    def update(self, E=None, **F):
        super(CaseInsensitiveDict, self).update(self.__class__(E))
        super(CaseInsensitiveDict, self).update(self.__class__(**F))


def conf_to_dict(configuration):
    # type: (str) -> CaseInsensitiveDict[str, Union[Dict[str, str], asciicast.AsciiCastTheme]]
    """Read a configuration string in INI format and return a dictionary

    Raise a subclass of configparser.Error if parsing the configuration string fails
    Raise AsciiCastError if the color theme is invalid
    """
    parser = configparser.ConfigParser(dict_type=CaseInsensitiveDict,
                                       comment_prefixes=(';',))
    parser.read_string(configuration)
    config_dict = CaseInsensitiveDict({
        'global': {
            'font': parser.get('global', 'font'),
            'theme': parser.get('global', 'theme'),
        }
    })

    themes = [theme.lower() for theme in parser.sections() if theme.lower() != 'global']
    for theme_name in themes:
        fg = parser.get(theme_name, 'foreground', fallback=None)
        bg = parser.get(theme_name, 'background', fallback=None)
        palette = ':'.join(parser.get(theme_name, 'color{}'.format(i), fallback='')
                           for i in range(16))

        try:
            config_dict[theme_name] = asciicast.AsciiCastV2Theme(fg, bg, palette)
        except asciicast.AsciiCastError:
            logger.error('Failed parsing color theme "{}"'.format(theme_name))
            raise

    return config_dict


def get_configuration(user_config, default_config):
    # type: (str, str) -> Dict[str, Union[Dict[str, str], asciicast.AsciiCastTheme]]
    """ Return a dictionary representing the configuration of the application. Default
    configuration is overrided by user configuration
    """
    config_dict = conf_to_dict(default_config)
    try:
        user_config_dict = conf_to_dict(user_config)
    except (configparser.Error, asciicast.AsciiCastError) as e:
        logger.info('Invalid configuration file: {}'.format(e))
        logger.info('Falling back to default configuration')
        user_config_dict = {}

    # Override default values with user configuration
    for section in user_config_dict:
        if section.lower() == 'global':
            for _property in 'theme', 'font':
                config_dict['GLOBAL'][_property] = user_config_dict['global'][_property]
        else:
            config_dict[section] = user_config_dict[section]

    return config_dict


def init_read_conf():
    if 'XDG_CONFIG_HOME' in os.environ:
        user_config_dir = os.environ['XDG_CONFIG_HOME']
    elif 'HOME' in os.environ:
        user_config_dir = os.path.join(os.environ['HOME'], '.config')
    else:
        logger.info('Environment variable XDG_CONFIG_HOME and HOME are not set: user '
                    'configuration cannot be used')
        user_config_dir = None

    if user_config_dir is None:
        return get_configuration(DEFAULT_CONFIG, DEFAULT_CONFIG)

    config_dir = os.path.join(user_config_dir, 'termtosvg')
    config_path = os.path.join(config_dir, 'termtosvg.ini')
    try:
        with open(config_path, 'r') as config_file:
            user_config = config_file.read()
    except FileNotFoundError:
        user_config = DEFAULT_CONFIG
        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, 'w') as config_file:
            config_file.write(DEFAULT_CONFIG)
        logger.info('Created user configuration file: {}'.format(config_path))

    return get_configuration(user_config, DEFAULT_CONFIG)

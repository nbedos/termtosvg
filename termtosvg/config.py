import configparser
import logging
import os
from typing import Union, Dict

import pkg_resources

import termtosvg.asciicast as asciicast

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

_PKG_CONFIGURATION_PATH = os.path.join('data', 'termtosvg.ini')
DEFAULT_CONFIG = pkg_resources.resource_string(__name__, _PKG_CONFIGURATION_PATH).decode('utf-8')


if 'XDG_CONFIG_HOME' in os.environ:
    USER_CONFIG_DIR = os.environ['XDG_CONFIG_HOME']
elif 'HOME' in os.environ:
    USER_CONFIG_DIR = os.path.join(os.environ['HOME'], '.config')
else:
    logger.info('Environment variable XDG_CONFIG_HOME and HOME are not set: user configuration '
                'cannot be used')
    USER_CONFIG_DIR = None


def conf_to_dict(configuration):
    # type: (str) -> Dict[str, Union[Dict[str, str], asciicast.AsciiCastTheme]]
    """Read a configuration string in INI format and return a dictionary

    Raise a subclass of configparser.Error if parsing the configuration string fails
    Raise ValueError if the color theme is invalid
    """
    user_config = configparser.ConfigParser(comment_prefixes=(';',))
    user_config.read_string(configuration)
    config_dict = {
        'GLOBAL': {
            'font': user_config.get('GLOBAL', 'font'),
            'theme': user_config.get('GLOBAL', 'theme'),
        }
    }

    themes = user_config.sections()
    themes.remove('GLOBAL')
    for theme_name in themes:
        fg = user_config.get(theme_name, 'foreground', fallback='')
        bg = user_config.get(theme_name, 'background', fallback='')
        palette = ':'.join(user_config.get(theme_name, 'color{}'.format(i), fallback='')
                           for i in range(16))

        # This line raises ValueError if the color theme is invalid
        config_dict[theme_name] = asciicast.AsciiCastTheme(fg, bg, palette)

    return config_dict


def get_configuration(user_config, default_config):
    # type: (str, str) -> Dict[str, Union[Dict[str, str], asciicast.AsciiCastTheme]]
    """ Return a dictionary representing the configuration of the application. Default
    configuration is overrided by user configuration
    """
    config_dict = conf_to_dict(default_config)
    try:
        user_config_dict = conf_to_dict(user_config)
    except (configparser.Error, ValueError) as e:
        logger.info('Invalid configuration file: {}'.format(e))
        logger.info('Falling back to default configuration')
        user_config_dict = {}

    # Override default values with user configuration
    for section in user_config_dict:
        if section == 'GLOBAL':
            for _property in 'theme', 'font':
                if _property in user_config_dict['GLOBAL']:
                    config_dict['GLOBAL'][_property] = user_config_dict['GLOBAL'][_property]
        else:
            config_dict[section] = user_config_dict[section]

    return config_dict


def init_read_conf(user_config_dir=USER_CONFIG_DIR, default_config=DEFAULT_CONFIG):
    config_dir = os.path.join(user_config_dir, 'termtosvg')
    config_path = os.path.join(config_dir, 'termtosvg.ini')
    try:
        with open(config_path, 'r') as config_file:
            user_config = config_file.read()
    except FileNotFoundError:
        user_config = DEFAULT_CONFIG
        try:
            with open(config_path, 'w') as config_file:
                config_file.write(DEFAULT_CONFIG)
            logger.info('Created default configuration file: {}'.format(config_path))
        except FileNotFoundError:
            os.makedirs(config_dir)
            with open(config_path, 'w') as config_file:
                config_file.write(DEFAULT_CONFIG)
            logger.info('Created default configuration file: {}'.format(config_path))

    return get_configuration(user_config, default_config)

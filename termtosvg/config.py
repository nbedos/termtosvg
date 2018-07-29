import configparser
import logging
import os
import pkgutil
from typing import Union, Dict

import termtosvg.asciicast as asciicast

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

PKG_CONF_PATH = 'data/termtosvg.ini'
PKG_TEMPLATE_PATH = 'data/templates'

# Listing templates here is not ideal but importing pkg_resources to get resource_listdir
# does not seem worth it: it adds a dependency and slows down the invocation of termtosvg
# by 150ms ('time termtosvg --help' execution time goes from 200ms to 350ms)
DEFAULT_TEMPLATES_NAMES = ['plain.svg', 'carbon.svg', 'progress_bar.svg', 'carbon_js.svg']


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

    def update(self, other=None, **kwargs):
        if other is None:
            other = {}
        super(CaseInsensitiveDict, self).update(self.__class__(other, **kwargs))


def validate_geometry(screen_geometry):
    # Will raise ValueError if the right hand side is made of more or less than two values,
    # or if the values can't be turned into integers
    columns, rows = [int(value) for value in screen_geometry.lower().split('x')]
    if columns <= 0 or rows <= 0:
        raise ValueError('Invalid value for screen-geometry option: "{}"'
                         .format(screen_geometry))
    return columns, rows


def conf_to_dict(configuration):
    # type: (str) -> CaseInsensitiveDict[str, Union[Dict[str, str], asciicast.AsciiCastV2Theme]]
    """Read a configuration string in INI format and return a dictionary

    Raise a subclass of configparser.Error if parsing the configuration string fails
    Raise AsciiCastError if the color theme is invalid
    """
    parser = configparser.ConfigParser(dict_type=CaseInsensitiveDict,
                                       comment_prefixes=(';',))
    parser.read_string(configuration)
    config_dict = CaseInsensitiveDict({
        'global': CaseInsensitiveDict({})
    })

    for option in ('font', 'theme', 'template', 'screen-geometry'):
        if option in parser['global']:
            config_dict['global'][option] = parser.get('global', option)

    # Convert screen-geometry option to tuple of integers
    if config_dict['global'].get('screen-geometry') is not None:
        config_dict['global']['screen-geometry'] = validate_geometry(config_dict['global']['screen-geometry'])

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


def init_read_conf():
    if 'XDG_CONFIG_HOME' in os.environ:
        user_config_dir = os.environ['XDG_CONFIG_HOME']
    elif 'HOME' in os.environ:
        user_config_dir = os.path.join(os.environ['HOME'], '.config')
    else:
        logger.info('Environment variable XDG_CONFIG_HOME and HOME are not set: user '
                    'configuration cannot be used')
        user_config_dir = None

    if user_config_dir is not None:
        termtosvg_config_dir = os.path.join(user_config_dir, 'termtosvg')

        # CONFIGURATION FILE
        config_file_path = os.path.join(termtosvg_config_dir, 'termtosvg.ini')
        try:
            with open(config_file_path, 'r') as config_file:
                user_config = config_file.read()
        except FileNotFoundError:
            # If there is no configuration file, create it from the default config
            user_config = pkgutil.get_data(__name__, PKG_CONF_PATH).decode('utf-8')
            os.makedirs(termtosvg_config_dir, exist_ok=True)
            with open(config_file_path, 'w') as config_file:
                config_file.write(user_config)
            logger.info('Created user configuration file: {}'.format(config_file_path))

        # SVG TEMPLATES
        templates_dir = os.path.join(termtosvg_config_dir, 'templates')
        try:
            # Gather templates in the user's configuration directory
            user_templates = {}
            for template_name in os.listdir(templates_dir):
                if template_name.endswith('.svg'):
                    template_path = os.path.join(templates_dir, template_name)
                    with open(template_path, 'rb') as template_file:
                        bstream = template_file.read()
                    user_templates[template_name[:-4]] = bstream
        except FileNotFoundError:
            # If the user has no 'templates' directory, create it and populate it with default
            # templates
            user_templates = {}
            os.mkdir(templates_dir)
            for template_name in DEFAULT_TEMPLATES_NAMES:
                pkg_template_path = '{}/{}'.format(PKG_TEMPLATE_PATH, template_name)
                bstream = pkgutil.get_data(__name__, pkg_template_path)
                user_template_path = os.path.join(templates_dir, template_name)
                with open(user_template_path, 'wb') as template_file:
                    template_file.write(bstream)
                assert template_name.endswith('.svg')
                user_templates[template_name[:-4]] = bstream
            logger.info('Created user templates directory: {}'.format(templates_dir))

        if not user_templates:
            raise ValueError('At least one template must be defined in the configuration directory')

        try:
            return conf_to_dict(user_config), user_templates
        except (configparser.Error, asciicast.AsciiCastError, ValueError) as exc:
            logger.info('Invalid configuration file: {}'.format(exc))
            logger.info('Falling back to default configuration')

    default_config = pkgutil.get_data(__name__, PKG_CONF_PATH).decode('utf-8')
    default_templates = {}
    for template_name in DEFAULT_TEMPLATES_NAMES:
        pkg_template_path = '{}/{}'.format(PKG_TEMPLATE_PATH, template_name)
        bstream = pkgutil.get_data(__name__, pkg_template_path)
        default_templates[template_name] = bstream

    return conf_to_dict(default_config), default_templates

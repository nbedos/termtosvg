import pkgutil

PKG_TEMPLATE_PATH = 'data/templates'

# Listing templates here is not ideal but importing pkg_resources to get resource_listdir
# does not seem worth it: it adds a dependency and slows down the invocation of termtosvg
# by 150ms ('time termtosvg --help' execution time goes from 200ms to 350ms)
DEFAULT_TEMPLATES_NAMES = [
    'gjm8.svg',
    'gjm8_play.svg',
    'gjm8_single_loop.svg',
    'dracula.svg',
    'solarized_dark.svg',
    'solarized_light.svg',
    'base16_default_dark.svg',
    'progress_bar.svg',
    'window_frame.svg',
    'window_frame_js.svg'
]


def validate_geometry(screen_geometry):
    """Raise ValueError if 'screen_geometry' does not conform to <integer>x<integer> format"""
    columns, rows = [int(value) for value in screen_geometry.lower().split('x')]
    if columns <= 0 or rows <= 0:
        raise ValueError('Invalid value for screen-geometry option: "{}"'.format(screen_geometry))
    return columns, rows


def default_templates():
    """Return mapping between the name of a template and the SVG template itself"""
    templates = {}
    for template_name in DEFAULT_TEMPLATES_NAMES:
        pkg_template_path = '{}/{}'.format(PKG_TEMPLATE_PATH, template_name)
        bstream = pkgutil.get_data(__name__, pkg_template_path)
        suffix = '.svg'
        if template_name.endswith(suffix):
            templates[template_name[:-len(suffix)]] = bstream
        else:
            templates[template_name] = bstream

    return templates

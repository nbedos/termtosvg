import pkgutil

PKG_TEMPLATE_PATH = 'data/templates'

# Listing templates here is not ideal but importing pkg_resources to get resource_listdir
# does not seem worth it: it adds a dependency and slows down the invocation of termtosvg
# by 150ms ('time termtosvg --help' execution time goes from 200ms to 350ms)
DEFAULT_TEMPLATES_NAMES = [
    'gjm8.svg',
    'dracula.svg',
    'solarized_dark.svg',
    'solarized_light.svg',
    'progress_bar.svg',
    'window_frame.svg',
    'window_frame_js.svg'
]


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
        raise ValueError('Invalid value for screen-geometry option: "{}"'.format(screen_geometry))
    return columns, rows


def default_templates():
    templates = CaseInsensitiveDict()
    for template_name in DEFAULT_TEMPLATES_NAMES:
        pkg_template_path = '{}/{}'.format(PKG_TEMPLATE_PATH, template_name)
        bstream = pkgutil.get_data(__name__, pkg_template_path)
        suffix = '.svg'
        if template_name.endswith(suffix):
            templates[template_name[:-len(suffix)]] = bstream
        else:
            templates[template_name] = bstream

    return templates

#!/usr/bin/env python

from distutils.core import setup

setup(
    name='vectty',
    version='0.1',
    description='Record terminal sessions as SVG animations',
    package_dir = {'': 'src'},
    py_modules=['vectty'],
    install_requires=[
        'pyte',
        'python-xlib',
        'svgwrite'
    ]
)

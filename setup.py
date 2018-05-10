#!/usr/bin/env python

from distutils.core import setup

setup(
    name='svg',
    version='0.1',
    packages=['src'],
    install_requires=[
        'pyte',
        'shapely',
        'svgwrite',
    ]
)

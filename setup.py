#!/usr/bin/env python

from setuptools import setup

setup(
    name='termtosvg',
    version='0.1',
    description='Record terminal sessions as SVG animations',
    packages=['termtosvg'],
    package_data={
        '': [
            'LICENSE'
        ],
        'termtosvg': [
            'data/Xresources/base16-*.Xresources',
            'data/Xresources/LICENSE.md',
        ]
    },
    py_modules=['termtosvg.anim', 'termtosvg.term'],
    entry_points={
        'console_scripts': [
            'termtosvg=termtosvg.__main__:main'
        ]
    },
    install_requires=[
        'setuptools',
        'pyte',
        'python-xlib',
        'svgwrite'
    ],
    extras_require={
        'dev': [
            'coverage',
        ]
    }
)

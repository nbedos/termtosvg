#!/usr/bin/env python

from setuptools import setup

setup(
    name='vectty',
    version='0.1',
    description='Record terminal sessions as SVG animations',
    packages=['vectty'],
    package_data={
        '': [
            'LICENSE'
        ],
        'vectty': [
            'data/Xresources/base16-*.Xresources',
            'data/Xresources/LICENSE.md',
        ]
    },
    py_modules=['vectty.anim', 'vectty.term'],
    entry_points={
        'console_scripts': [
            'vectty=vectty.__main__:main'
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

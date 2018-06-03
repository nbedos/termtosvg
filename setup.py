#!/usr/bin/env python

from setuptools import setup

setup(
    name='vectty',
    version='0.1',
    description='Record terminal sessions as SVG animations',
    packages=['vectty'],
    py_modules=['vectty.anim', 'vectty.term'],
    entry_points={
        'console_scripts': [
            'vectty=vectty.__main__:main'
        ]
    },
    install_requires=[
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

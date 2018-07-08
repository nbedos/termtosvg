#!/usr/bin/env python

from setuptools import setup

setup(
    name='termtosvg',
    version='0.4.0',
    licence='BSD 3-clause license',
    author='Nicolas Bedos',
    description='Record terminal sessions as SVG animations',
    long_description='A Linux terminal recorder written in Python '
                     'which renders your command line sessions as '
                     'standalone SVG animations.',
    url='https://github.com/nbedos/termtosvg',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: System :: Shells',
        'Topic :: Terminals'
    ],
    packages=['termtosvg'],
    package_data={
        '': [
            'LICENSE'
        ],
        'termtosvg': [
            'data/LICENSE.md',
            'data/termtosvg.ini',
        ]
    },
    py_modules=[
        'termtosvg.anim',
        'termtosvg.asciicast',
        'termtosvg.config',
        'termtosvg.term',
    ],
    entry_points={
        'console_scripts': [
            'termtosvg=termtosvg.__main__:main'
        ]
    },
    install_requires=[
        'pyte',
        'setuptools',
        'svgwrite'
    ],
    extras_require={
        'dev': [
            'coverage',
            'twine',
            'wheel',
        ]
    }
)

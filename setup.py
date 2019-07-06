#!/usr/bin/env python

from setuptools import setup

setup(
    name='termtosvg',
    version='0.9.0',
    license='BSD 3-clause license',
    author='Nicolas Bedos',
    author_email='nicolas.bedos@gmail.com',
    description='Record terminal sessions as SVG animations',
    long_description='A Linux terminal recorder written in Python '
                     'which renders your command line sessions as '
                     'standalone SVG animations.',
    url='https://github.com/nbedos/termtosvg',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: BSD',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: System :: Shells',
        'Topic :: Terminals'
    ],
    python_requires='>=3.5',
    packages=[
        'termtosvg',
        'termtosvg.tests'
    ],
    scripts=['scripts/termtosvg'],
    include_package_data=True,
    install_requires=[
        'lxml',
        'pyte',
        'wcwidth',
    ],
    extras_require={
        'dev': [
            'coverage',
            'pylint',
            'twine',
            'wheel',
        ]
    }
)

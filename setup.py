#!/usr/bin/env python

import mebo

from setuptools import (
    setup,
    find_packages
)


def find_requirements(filename='requirements.txt'):
    with open(filename, 'r') as f:
        return f.readlines()


def readme(filename='README.md'):
    with open(filename, 'r') as f:
        return f.read()

setup(
    name='mebo',
    version=mebo.__version__,
    description='Simple python interface to control the mebo toy robot',
    long_description=readme(),
    author='Cameron Lane',
    author_email='crlane@adamanteus.com',
    url='https://github.com/crlane/python-mebo',
    packages=find_packages(exclude=['contrib', 'docs', 'test*']),
    install_requires=find_requirements(),
    license='MIT',
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 2 - Pre-Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Education',
        'Topic :: Scientific/Engineering :: Human Machine Interfaces',
        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)

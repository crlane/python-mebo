#!/usr/bin/env python
import os
from setuptools import (
    setup,
    find_packages
)

# NOTE: thanks @kennethreitz for the inspiration here. ;)
here = os.path.abspath(os.path.dirname(__file__))
about = {}
with open(os.path.join(here, 'mebo', '__version__.py'), 'r') as f:
    exec(f.read(), about)


def find_requirements(filename='requirements.txt'):
    with open(filename, 'r') as f:
        return f.readlines()


def readme(filename='README.rst'):
    with open(filename, 'r') as f:
        return f.read()

setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description=readme(),
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    package_data={'': ['LICENSE.md']},
    packages=find_packages(exclude=['contrib', 'docs', 'test*']),
    install_requires=find_requirements(),
    license=about['__license__'],
    extras_require={
        'testing': find_requirements('test_requirements.txt'),
        'development': ['ipython', 'ipdb']
    },
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Education',
        'Topic :: Scientific/Engineering :: Human Machine Interfaces',
        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)

#!/usr/bin/env python

from setuptools import (
    setup,
    find_packages
)


__VERSION__ = '0.1.0-dev'


def find_requirements(filename='requirements.txt'):
    with open(filename, 'r') as f:
        return f.readlines()


setup(
    name='mebo',
    version=__VERSION__,
    description='Simple API to control the mebo toy robot with Python',
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
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)

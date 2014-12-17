#!/usr/bin/env python3
"""NITE Setup module."""
from setuptools import setup, find_packages
import os


def read(fname):
    """Read and return the contents of a file."""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='nite',
    version='0.0.1',
    description='NITE - Nigh Impervious Task Executor',
    long_description=read('README'),
    author='Kalman Olah',
    author_email='hello@kalmanolah.net',
    url='https://github.com/kalmanolah/nite',
    license='MIT',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
    ],

    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'nite = nite:nite',
        ],
    },

    install_requires=[
        'amqp',
        'setproctitle',
        'msgpack-python',
        'click',
        'ballercfg',
        'colorlog'
    ],
    dependency_links=[
        'git+https://github.com/kalmanolah/ballercfg.git',
    ],
)

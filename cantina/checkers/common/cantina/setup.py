#!/usr/bin/env python
from distutils.core import setup

setup(
    name='CANtina Common Library',
    version='0.1',
    description='Common code required across CANtina components',
    packages=['cantina', 'cantina.canopy', 'cantina.kex', 'cantina.powcheck', 'cantina.tocan'],
    install_requires=[
        'cryptography == 37.0.4',
        'msgpack == 1.0.4',
        'python-can == 4.0.0',
        'janus'
    ],
    python_requiers='>=3.10'
)

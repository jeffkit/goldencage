#!/usr/bin/env python

from setuptools import setup, find_packages
from goldencage import VERSION

url = "https://github.com/jeffkit/goldencage"

long_description = "virtual coin & task management for mobile app (specially for china)"

setup(
    name="goldencage",
    version=VERSION,
    description=long_description,
    maintainer="jeff kit",
    maintainer_email="bbmyth@gmail.com",
    url=url,
    long_description=long_description,
    packages=find_packages('.'),
    zip_safe=False,
    install_requires=[
        'requests',
        'wechat',
        'pycrypto',
        'dicttoxml',
        'xmltodict',
    ]
)

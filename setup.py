#!/usr/bin/env python
# -*- coding: utf-8 -*-

# setup.py

from setuptools import setup, find_packages
from dvhaedit.main import VERSION


with open('requirements.txt', 'r') as doc:
    requires = [line.strip() for line in doc]

with open('README.md', 'r') as doc:
    long_description = doc.read()


setup(
    name='dvha-edit',
    include_package_data=True,
    python_requires='>3.5',
    packages=find_packages(),
    version=VERSION,
    description='Simple DICOM tag editor built with wxPython and pydicom',
    author='Dan Cutright',
    author_email='dan.cutright@gmail.com',
    url='https://github.com/cutright/DVHA-DICOM-Editor',
    download_url='https://github.com/cutright/DVHA-DICOM-Editor.git',
    license="BSD License",
    keywords=['dicom', 'wxpython', 'pydicom'],
    classifiers=[],
    install_requires=requires,
    entry_points={'console_scripts': ['dvhaedit = dvhaedit.main:start']},
    long_description=long_description,
    long_description_content_type="text/markdown"
)

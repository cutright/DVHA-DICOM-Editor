#!/usr/bin/env python
# -*- coding: utf-8 -*-

# setup.py

from setuptools import setup, find_packages
from dvhaedit._version import __version__


with open('requirements.txt', 'r') as doc:
    requires = [line.strip() for line in doc]

with open('README.md', 'r') as doc:
    long_description = doc.read()

CLASSIFIERS = [
    "License :: OSI Approved :: MIT License",
    "Intended Audience :: End Users/Desktop",
    "Intended Audience :: Healthcare Industry",
    "Intended Audience :: Science/Research",
    "Natural Language :: English",
    "Development Status :: 4 - Beta",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3 :: Only",
    "Operating System :: OS Independent",
    "Topic :: Scientific/Engineering :: Medical Science Apps.",
    "Topic :: Scientific/Engineering :: Physics"]


setup(
    name='dvha-edit',
    include_package_data=True,
    python_requires='>3.5',
    packages=find_packages(),
    version=__version__,
    description='Simple DICOM tag editor built with wxPython and pydicom',
    maintainer="Dan Cutright",
    maintainer_email="dan.cutright@gmail.com",
    author='Dan Cutright',
    author_email='dan.cutright@gmail.com',
    url='https://github.com/cutright/DVHA-DICOM-Editor',
    download_url='https://github.com/cutright/DVHA-DICOM-Editor/archive/master.zip',
    license="MIT License",
    keywords=['dicom', 'wxpython', 'pydicom', 'pyinstaller'],
    classifiers=CLASSIFIERS,
    install_requires=requires,
    entry_points={'console_scripts': ['dvhaedit = dvhaedit.main:start']},
    long_description=long_description,
    long_description_content_type="text/markdown"
)

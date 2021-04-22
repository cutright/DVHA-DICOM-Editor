#!/usr/bin/env python
# -*- coding: utf-8 -*-

# paths.py
"""
A collection of directories and paths updated with the script directory
"""
# Copyright (c) 2020 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVHA-DICOM-Editor

import sys
from os.path import join, dirname

SCRIPT_DIR = dirname(__file__)
PARENT_DIR = getattr(
    sys, "_MEIPASS", dirname(SCRIPT_DIR)
)  # PyInstaller compatibility
RESOURCES_DIR = join(SCRIPT_DIR, "resources")
LICENSE_PATH = join(PARENT_DIR, "LICENSE.txt")
DYNAMIC_VALUE_HELP = join(RESOURCES_DIR, "dynamic_value_help.txt")
ICONS_DIR = join(RESOURCES_DIR, "icons")
ANON_TEMPLATE = join(RESOURCES_DIR, "anonymize.pickle")
WIN_APP_ICON = join(ICONS_DIR, "dvha-edit.ico")
WIN_FRAME_ICON = join(ICONS_DIR, "dvha-edit_frame.ico")
MAC_APP_ICON = join(ICONS_DIR, "dvha-edit.icns")

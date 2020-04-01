#!/usr/bin/env python
# -*- coding: utf-8 -*-

# options.py
"""
Classes containing user preferences
"""
# Copyright (c) 2020 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVHA-DICOM-Editor

from dvhaedit.dicom_editor import get_uid_prefixes


class Options:
    def __init__(self):
        # DICOM options
        self.prefix = ''
        self.prefix_dict = get_uid_prefixes()
        self.entropy_source = ''

        # Random Number generator
        self.rand_digits = 5

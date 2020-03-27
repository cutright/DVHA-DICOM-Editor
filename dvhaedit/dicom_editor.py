#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dicom_editor.py
"""
Classes used to edit pydicom datasets
"""
# Copyright (c) 2020 Dan Cutright
# This file is part of DVHA DICOM Editor, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVHA-DICOM-Editor


import pydicom


class DICOMEditor:
    def __init__(self, dcm):
        if type(dcm) is not pydicom.dataset.FileDataset:
            self.dcm = pydicom.read_file(dcm, stop_before_pixels=True, force=True)
        else:
            self.dcm = dcm

    def edit_tag(self, tag, new_value):
        self.dcm[tag].value = new_value

    def get_tag_value(self, tag):
        return self.dcm[tag].value

    def get_tag_name(self, tag):
        return self.dcm[tag].name

    def get_tag_type(self, tag):
        return str(type(self.dcm[tag].value)).split("'")[1]

    def save_as(self, file_path):
        self.dcm.save_as(file_path)

    @property
    def modality(self):
        try:
            return self.dcm.Modality
        except Exception:
            return 'Not Found'


class Tag:
    def __init__(self, group, element):
        self.group = group.zfill(4)
        self.element = element.zfill(4)
        self.tag = tuple(['0x%s' % v for v in [self.group, self.element]])

    def __str__(self):
        return "(%s, %s)" % (self.group, self.element)

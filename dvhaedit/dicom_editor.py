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
    """DICOM editing and value getter class"""
    def __init__(self, dcm):
        """
        :param dcm: either a file_path to a DICOM file or a pydicom FileDataset
        """
        if type(dcm) is not pydicom.dataset.FileDataset:
            self.dcm = pydicom.read_file(dcm, stop_before_pixels=True, force=True)
        else:
            self.dcm = dcm

    def edit_tag(self, tag, new_value):
        """
        Change a DICOM tag value
        :param tag: the DICOM tag of interest
        :type tag: Tag
        :param new_value: new value of the DICOM tag
        """
        self.dcm[tag].value = new_value

    def get_tag_value(self, tag):
        """
        Get the current value of the provided DICOM tag
        :param tag: the DICOM tag of interest
        :type tag: Tag
        """
        return self.dcm[tag].value

    def get_tag_name(self, tag):
        """
        Get the DICOM tag attribute (name)
        :param tag: the DICOM tag of interest
        :type tag: Tag
        """
        return self.dcm[tag].name

    def get_tag_type(self, tag):
        """
        Get the DICOM tag data type
        :param tag: the DICOM tag of interest
        :type tag: Tag
        """
        return str(type(self.dcm[tag].value)).split("'")[1]

    def save_as(self, file_path):
        """
        Save the dataset to a DICOM file with pydicom
        :param file_path: absolute file path
        :type file_path: str
        """
        self.dcm.save_as(file_path)

    @property
    def modality(self):
        """
        Get the DICOM file type (Modality)
        :return: DICOM file modality
        :rtype: str
        """
        try:
            return str(self.dcm.Modality)
        except Exception:
            return 'Not Found'


class Tag:
    """Convert group and element strings into a keyword/tag for pydicom"""
    def __init__(self, group, element):
        """
        :param group: first paramater in a DICOM tag
        :type group: str
        :param element: first paramater in a DICOM tag
        :type element: str
        """
        self.group = self.process_string(group)
        self.element = self.process_string(element)

    def __str__(self):
        """Override str operator to return a representation for GUI"""
        return "(%s, %s)" % (self.group, self.element)

    @property
    def tag(self):
        """Get keyword/tag suitable for pydicom"""
        return tuple(['0x%s' % v for v in [self.group, self.element]])

    @staticmethod
    def process_string(string):
        """
        Clean a string for tag generation
        :param string: group or element string
        :type string: str
        :return: processed string
        :rtype: str
        """
        return string.replace('0x', '').strip().zfill(4)

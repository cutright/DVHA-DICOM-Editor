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
from pydicom.datadict import keyword_dict, get_entry
from pydicom._dicom_dict import DicomDictionary
from dvhaedit.utilities import remove_non_alphanumeric, get_sorted_indices


keyword_dict.pop('')  # remove the empty keyword


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

    @property
    def tag_as_int(self):
        if self.has_x:
            return None
        string = "0x%s%s" % (self.group, self.element)
        return int(string, 16)

    @property
    def has_x(self):
        """Some retired Tags from pydicom.datadict may have an x placeholder"""
        return 'X' in self.group or 'X' in self.element

    @staticmethod
    def process_string(string):
        """
        Clean a string for tag generation
        :param string: group or element string
        :type string: str
        :return: processed string
        :rtype: str
        """
        if string.startswith('0x'):
            string = string[2:]
        return remove_non_alphanumeric(string).zfill(4).upper()

    @property
    def vr(self):
        if not self.has_x and self.group and self.element:
            try:
                return get_entry(self.tag_as_int)[0]
            except KeyError:
                pass
        return 'Not Found'


class TagSearch:
    """Class used to find partial tag keyword matches"""
    def __init__(self):
        self.keywords = list(keyword_dict)
        self.lower_case_map = {key.lower(): key for key in self.keywords}

    def __call__(self, search_str):
        return self.get_table_data(search_str)

    def get_keyword_matches(self, partial_keyword):
        if partial_keyword:
            partial_keyword = remove_non_alphanumeric(partial_keyword).lower()
            return [self.lower_case_map[key] for key in self.lower_case_map if partial_keyword in key]
        return self.keywords

    def get_matches(self, partial_keyword):
        if partial_keyword:
            partial_keyword = remove_non_alphanumeric(partial_keyword).lower()
            return {tag: entry for tag, entry in DicomDictionary.items()
                    if partial_keyword in entry[4].lower() or
                    partial_keyword in remove_non_alphanumeric(str(self.int_to_tag(tag)))}
        else:
            return DicomDictionary

    @staticmethod
    def keyword_to_tag(keyword):
        tag = str(hex(keyword_dict.get(keyword)))
        group = tag[0:-4]
        element = tag[-4:]
        return Tag(group, element)

    @staticmethod
    def hex_to_tag(tag_as_hex):
        tag = str(tag_as_hex).zfill(8)
        group = tag[0:-4]
        element = tag[-4:]
        return Tag(group, element)

    def int_to_tag(self, tag_as_int):
        return self.hex_to_tag(str(hex(tag_as_int))[2:])

    @staticmethod
    def get_value_rep(tag_as_int):
        if tag_as_int is not None:
            return get_entry(tag_as_int)[0]
        return 'Unknown'

    def get_table_data(self, search_str):
        columns = ['Keyword', 'Tag', 'VR']

        data = [(en[4], self.int_to_tag(tg), en[0]) for tg, en in self.get_matches(search_str).items() if en[4]]

        keywords = [row[0] for row in data]
        sorted_indices = get_sorted_indices(keywords)

        keywords = [data[i][0] for i in sorted_indices]
        tags = [data[i][1] for i in sorted_indices]
        value_reps = [data[i][2] for i in sorted_indices]

        data = {'Keyword': keywords, 'Tag': tags, 'VR': value_reps}
        return {'data': data, 'columns': columns}

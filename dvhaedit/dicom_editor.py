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
from pydicom._uid_dict import UID_dictionary
from dvhaedit.utilities import remove_non_alphanumeric, get_sorted_indices


keyword_dict.pop('')  # remove the empty keyword


class DICOMEditor:
    """DICOM editing and value getter class"""
    def __init__(self, dcm):
        """
        :param dcm: either a file_path to a DICOM file or a pydicom FileDataset
        """
        if type(dcm) is not pydicom.dataset.FileDataset:
            self.dcm = pydicom.read_file(dcm, force=True)
        else:
            self.dcm = dcm

        self.init_tag_values = {}
        self.tree = {}

        self.output_path = None

    def edit_tag(self, new_value, tag, address=None):
        """
        Change a DICOM tag value
        :param tag: the DICOM tag of interest
        :type tag: Tag
        :param new_value: new value of the DICOM tag
        :param address: an address is required for tags within sequences
        """
        if address is None:
            old_value = self.dcm[tag].value
            self.init_tag_values[tag] = old_value
            self.dcm[tag].value = new_value
        else:
            element = self.get_element(tag, address)
            old_value = element.value
            element.value = new_value
        return old_value, self.get_tag_value(tag, address)

    def sync_referenced_tag(self, keyword, old_value, new_value, check_all_tags=False):
        """
        Check if there is a Referenced tag with matching value, then set to new_value if so
        :param keyword: DICOM tag keyword
        :type keyword: str
        :param old_value: if Referenced+keyword tag value is this value, update to new_value
        :param new_value: new value of tag if connected
        :param check_all_tags: Set to True to check every tag in the dataset,
        otherwise only SQ and tags with Referenced in their keywords
        :type check_all_tags: bool
        """
        if check_all_tags:
            addresses = self.find_all_tags_with_value(old_value, vr='UI')
        else:
            tag = keyword_dict.get("Referenced%s" % keyword)
            addresses = self.find_tag(tag, referenced_mode=True)

        for address in addresses:
            tag = address[-1][0]
            if self.get_tag_value(tag, address=address) == old_value:
                self.edit_tag(new_value, tag, address=address)

    def get_tag_value(self, tag, address=None):
        """
        Get the current value of the provided DICOM tag
        :param tag: the DICOM tag of interest
        :type tag: Tag
        :param address: if tag is within a sequence, an address is needed which is a list of [tag, index]
        :type address: list
        """
        return self.get_element(tag, address).value

    def get_all_tag_values(self, tag):
        return list(set([address[-1][1] for address in self.find_tag(tag)]))

    def get_element(self, tag, address=None):
        """
        Get the element of the provided DICOM tag
        :param tag: the DICOM tag of interest
        :type tag: Tag
        :param address: if tag is within a sequence, an address is needed which is a list of [tag, index]
        :type address: list
        """
        if address is None:
            return self.dcm[tag]

        element = self.dcm
        for sequence in address[:-1]:  # Final item in address is [tag, None]
            tag_, index_ = tuple(sequence)
            element = element[tag_][index_]
        return element[tag]

    def get_tag_keyword(self, tag):
        """
        Get the DICOM tag attribute (name)
        :param tag: the DICOM tag of interest
        :type tag: Tag
        """
        return self.dcm[tag].keyword

    def get_tag_type(self, tag):
        """
        Get the DICOM tag data type
        :param tag: the DICOM tag of interest
        :type tag: Tag
        """
        return str(type(self.dcm[tag].value)).split("'")[1]

    def save_to_file(self, file_path=None):
        """
        Save the dataset to a DICOM file with pydicom
        :param file_path: absolute file path
        :type file_path: str
        """
        file_path = self.output_path if file_path is None else file_path
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

    def find_all_tags_with_vr(self, vr):
        return self.find_tag(None, vr=vr)

    def find_all_tags_with_value(self, value, vr=None):
        return self.find_tag(None, value=value, vr=vr)

    def find_tag(self, tag, vr=None, referenced_mode=False, value=None):
        """Find all instances of tag in the pydicom dataset, return tags and indices pointing to input tag"""
        # address is a list of all values for tag, with its location
        # each item in the list has a length equal to number of tags required to identify the value
        # Example:
        #   BeamMeterSet (300A, 0086) for RT PLan is accessed via FractionGroupSequence -> ReferencedBeamSequence
        #   Therefore, each row in addresses will be:
        #     [[<FractionGroupSequence tag>, index], [<ReferencedBeamSequence tag>, index], [<BeamMeterSet tag>, None]]
        # Addresses store the int representation of tag
        #
        # To find all tags with a specified VR, set vr and set tag to None

        addresses = []
        self._find_tag_instances(tag, self.dcm, addresses, vr=vr, referenced_mode=referenced_mode, value=value)
        return addresses

    def _find_tag_instances(self, tag, data_set, addresses, parent=None, vr=None, referenced_mode=False, value=None):
        """recursively walk through data_set sequences, collect addresses with the provided tag"""
        if referenced_mode:
            vr = 'UI'
        if parent is None:
            parent = []
        for elem in data_set:
            if not referenced_mode or 'Referenced' in elem.keyword:
                if hasattr(elem, 'VR') and elem.VR == 'SQ':
                    for i, seq_item in enumerate(elem):
                        self._find_tag_instances(tag, seq_item, addresses, parent + [[int(elem.tag), i]])
                elif tag is None or \
                        (hasattr(elem, 'tag') and (elem.tag == tag or
                                                   (referenced_mode and 'Referenced' in elem.keyword))):
                    if (vr is None or vr == elem.VR) and (value is None or (elem.VR == vr and elem.value == value)):
                        v = elem.value if hasattr(elem, 'value') else None
                        addresses.append(parent + [[int(elem.tag), v]])


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
        return self.get_entry('VR')

    @property
    def vm(self):
        return self.get_entry('VM')

    @property
    def name(self):
        return self.get_entry('name')

    @property
    def is_retired(self):
        return self.get_entry('is_retired')

    @property
    def keyword(self):
        return self.get_entry('keyword')

    def get_entry(self, tag_property):
        index = ['VR', 'VM', 'name', 'is_retired', 'keyword'].index(tag_property)
        if not self.has_x and self.group and self.element:
            try:
                return get_entry(self.tag_as_int)[index]
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


def save_dicom(data_set):
    """Helper function for the Save Worker/Thread"""
    data_set.save_to_file()


def get_uid_prefixes():
    prefix_dict = {}
    for prefix, data in UID_dictionary.items():
        if data[0]:
            key = "%s - %s" % (data[0], data[1])
            if data[3].lower() == 'retired':
                key = key + ' (Retired)'
            prefix_dict[key] = prefix
    return prefix_dict

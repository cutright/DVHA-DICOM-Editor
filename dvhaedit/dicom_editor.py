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

from os.path import basename, dirname
from pubsub import pub
import pydicom
from pydicom.datadict import keyword_dict, get_entry
from pydicom._dicom_dict import DicomDictionary
from dvhaedit.utilities import remove_non_alphanumeric, get_sorted_indices


keyword_dict.pop("")  # remove the empty keyword


class DICOMEditor:
    """DICOM editing and value getter class"""

    def __init__(self, file_path, force=False):
        """
        :param file_path: a file_path to a DICOM file
        """

        self.force = force
        self.file_path = file_path
        self.init_tag_values = {}
        self.history = []
        self.referenced_mode = False
        self.output_path = None
        self.dcm = None

        self.load_dcm()
        self.clear_dcm()

    def load_dcm(self):
        try:
            self.dcm = pydicom.read_file(self.file_path, force=self.force)
        except Exception:
            self.dcm = False

    def clear_dcm(self):
        if self.dcm is not False:
            self.dcm = None

    def validate_ds(self):
        """Check for required properties in the case of an InvalidDicomError"""
        required_keywords = [
            "StudyDate",
            "StudyTime",
            "PatientID",
            "StudyID",
            "SeriesNumber",
        ]
        if not all(
            [hasattr(self.dcm, keyword) for keyword in required_keywords]
        ):
            self.dcm = None

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
            address = [tag, old_value]
        else:
            element = self.get_element(tag, address)
            old_value = element.value
            element.value = new_value

        self.append_history(new_value, address)

        return old_value, self.get_tag_value(tag, address)

    def append_history(self, new_value, address):

        if type(new_value) is list:
            str_values = [str(v) for v in new_value]
            new_value_str = "[%s]" % ", ".join(str_values)
        else:
            new_value_str = str(new_value)

        if "," in new_value_str:
            new_value_str = '"%s"' % new_value_str

        line = ",".join(
            [
                str(len(self.history) + 1),
                self.address_to_string(address),
                str(new_value_str),
            ]
        )
        self.history.append(line)

    @staticmethod
    def address_to_string(address):
        line = []
        for item in address[:-1]:
            tag, index = item[0], item[1]
            keyword = DicomDictionary[tag][4]
            line.append("%s[%s]" % (keyword, index))
        tag, value = tuple(address[-1])
        keyword = DicomDictionary[tag][4]

        value_str = str(value)
        if "," in value_str:
            value = '"%s"' % value_str

        line.append("%s,%s" % (keyword, value))
        return ".".join(line)

    def sync_referenced_tag(
        self, keyword, old_value, new_value, check_all_tags=False
    ):
        """
        Check if there is a Referenced tag with matching value, then set to
        new_value if so
        :param keyword: DICOM tag keyword
        :type keyword: str
        :param old_value: if Referenced+keyword tag value is this value,
        update to new_value
        :param new_value: new value of tag if connected
        :param check_all_tags: Set to True to check every tag in the dataset,
        otherwise only SQ and tags with Referenced in their keywords
        :type check_all_tags: bool
        """
        if check_all_tags:
            addresses = self.find_all_tags_with_value(old_value, vr="UI")
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
        :param address: if tag is within a sequence, an address is needed
        which is a list of [tag, index]
        :type address: list
        """
        return self.get_element(tag, address).value

    def get_all_tag_values(self, tag):
        all_tag_values = []
        for address in self.find_tag(tag):
            v = address[-1][1]
            all_tag_values.append(v)

        return list(set(all_tag_values))

    def get_element(self, tag, address=None):
        """
        Get the element of the provided DICOM tag
        :param tag: the DICOM tag of interest
        :type tag: Tag
        :param address: if tag is within a sequence, an address is needed
        which is a list of [tag, index]
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

    def save_to_file(self, file_path=None):
        """
        Save the dataset to a DICOM file with pydicom
        :param file_path: absolute file path
        :type file_path: str
        """
        file_path = self.output_path if file_path is None else file_path
        self.dcm.save_as(file_path)
        # Load the new file if another edit is applied
        self.file_path = file_path

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
            return "Not Found"

    def find_all_tags_with_vr(self, vr):
        return self.find_tag(None, vr=vr)

    def find_all_tags_with_value(self, value, vr=None):
        return self.find_tag(None, value=value, vr=vr)

    def find_tag(self, tag, vr=None, referenced_mode=False, value=None):
        """Find all instances of tag in the pydicom dataset, return tags and
        indices pointing to input tag"""
        # address is a list of all values for tag, with its location
        # each item in the list has a length equal to number of tags required
        # to identify the value
        # Example:
        #   BeamMeterSet (300A, 0086) for RT PLan is accessed via
        #   FractionGroupSequence -> ReferencedBeamSequence
        #   Therefore, each row in addresses will be:
        #     [[<FractionGroupSequence tag>, index],
        #      [<ReferencedBeamSequence tag>, index],
        #      [<BeamMeterSet tag>, value]]
        # Addresses store the int representation of tag
        #
        # To find all tags with a specified VR, set vr and set tag to None

        addresses = []
        parent = []
        vr = "UI" if referenced_mode else vr
        self.referenced_mode = referenced_mode
        self._find_tag_instances(
            tag, self.dcm, addresses, parent, vr=vr, value=value
        )
        return addresses

    def _find_tag_instances(
        self, tag, data_set, addresses, parent, vr=None, value=None
    ):
        """recursively walk through data_set sequences, collect addresses with
        the provided tag"""
        for elem in data_set:
            if (
                hasattr(elem, "VR")
                and hasattr(elem, "keyword")
                and hasattr(elem, "tag")
            ):
                if not self.referenced_mode or "Referenced" in elem.keyword:
                    if elem.VR == "SQ":
                        for i, seq_item in enumerate(elem):
                            new_parent = parent + [[int(elem.tag), i]]
                            self._find_tag_instances(
                                tag, seq_item, addresses, new_parent
                            )
                    elif (
                        tag is None
                        or elem.tag == tag
                        or (
                            self.referenced_mode
                            and "Referenced" in elem.keyword
                        )
                    ):
                        if (vr is None or vr == elem.VR) and (
                            value is None
                            or (elem.VR == vr and elem.value == value)
                        ):
                            v = elem.value if hasattr(elem, "value") else None
                            address = parent + [[int(elem.tag), v]]
                            addresses.append(address)


class Tag:
    """Convert group and element strings into a keyword/tag for pydicom"""

    def __init__(self, group, element):
        """
        :param group: first parameter in a DICOM tag
        :type group: str
        :param element: second parameter in a DICOM tag
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
        return tuple(["0x%s" % v for v in [self.group, self.element]])

    @property
    def tag_as_int(self):
        """Convert DICOM tag to its integer representation"""
        if self.has_x:
            return None
        string = "0x%s%s" % (self.group, self.element)
        return int(string, 16)

    @property
    def has_x(self):
        """Some retired Tags from pydicom.datadict may have an x placeholder"""
        return "X" in self.group or "X" in self.element

    @staticmethod
    def process_string(string):
        """
        Clean a string for tag generation
        :param string: group or element string
        :type string: str
        :return: processed string
        :rtype: str
        """
        if string.startswith("0x"):
            string = string[2:]
        return remove_non_alphanumeric(string).zfill(4).upper()

    ###########################################################################
    # DICOM property getters
    ###########################################################################
    @property
    def vr(self):
        return self.get_entry("VR")

    @property
    def vm(self):
        return self.get_entry("VM")

    @property
    def name(self):
        return self.get_entry("name")

    @property
    def is_retired(self):
        return self.get_entry("is_retired")

    @property
    def keyword(self):
        return self.get_entry("keyword")

    def get_entry(self, tag_property):
        """General function for the getters in the code block"""
        index = ["VR", "VM", "name", "is_retired", "keyword"].index(
            tag_property
        )
        if not self.has_x and self.group and self.element:
            try:
                return get_entry(self.tag_as_int)[index]
            except KeyError:
                pass
        return "Not Found"


class TagSearch:
    """Class used to find partial tag keyword matches"""

    def __init__(self):
        self.keywords = list(keyword_dict)
        self.lower_case_map = {key.lower(): key for key in self.keywords}

    def __call__(self, search_str):
        return self.get_table_data(search_str)

    def get_table_data(self, search_str):
        """Return data for the ListCtrl in the main application"""
        columns = ["Keyword", "Tag", "VR"]

        data = [
            (en[4], self.int_to_tag(tg), en[0])
            for tg, en in self.get_matches(search_str).items()
            if en[4]
        ]

        keywords = [row[0] for row in data]
        sorted_indices = get_sorted_indices(keywords)

        keywords = [data[i][0] for i in sorted_indices]
        tags = [data[i][1] for i in sorted_indices]
        value_reps = [data[i][2] for i in sorted_indices]

        data = {"Keyword": keywords, "Tag": tags, "VR": value_reps}
        return {"data": data, "columns": columns}

    def get_matches(self, search_str):
        """
        Get matching tags in a pydicom._dicom_dict.DicomDictionary format
        :param search_str: a string for partial keyword of hex-tag match
        :return: partial matches
        :rtype: dict
        """
        if search_str:
            search_str = remove_non_alphanumeric(search_str).lower()
            return {
                tag: entry
                for tag, entry in DicomDictionary.items()
                if search_str in entry[4].lower()
                or search_str  # keyword match
                in remove_non_alphanumeric(str(self.int_to_tag(tag)))
            }  # hex tag match
        else:
            return DicomDictionary

    @staticmethod
    def keyword_to_tag(keyword):
        """
        Get a dvhaedit Tag from DICOM keyword
        :param keyword: DICOM keyword
        :type keyword: str
        :return: dvhaedit Tag class object
        :rtype: Tag
        """
        tag = str(hex(keyword_dict.get(keyword)))
        group = tag[0:-4]
        element = tag[-4:]
        return Tag(group, element)

    @staticmethod
    def hex_to_tag(tag_as_hex):
        """Convert a hex tag to Tag"""
        tag = str(tag_as_hex).zfill(8)
        group = tag[0:-4]
        element = tag[-4:]
        return Tag(group, element)

    def int_to_tag(self, tag_as_int):
        return self.hex_to_tag(str(hex(tag_as_int))[2:])

    @staticmethod
    def get_value_rep(tag_as_int):
        """Get DICOM VR with an integer DICOM tag"""
        if tag_as_int is not None:
            return get_entry(tag_as_int)[0]
        return "Unknown"


def save_dicom(data_set):
    """Helper function for the Save Worker/Thread"""
    data_set.save_to_file()


def apply_edits(values_dicts, all_row_data, data_sets):
    """Apply the tag edits to every file in self.ds, return any errors"""
    error_log, history = [], []
    for row in range(len(all_row_data)):

        row_data = all_row_data[row]
        tag = row_data["tag"]
        value_str = row_data["value_str"]
        keyword = row_data["keyword"]
        values_dict = values_dicts[row]

        for i, (file_path, ds) in enumerate(data_sets.items()):
            label = "Editing %s for file %s of %s" % (
                keyword,
                i + 1,
                len(data_sets),
            )
            msg = {"label": label, "gauge": float(i) / len(data_sets)}
            pub.sendMessage("progress_update", msg=msg)
            ds.load_dcm()
            try:
                if (
                    tag.tag in ds.dcm.keys()
                ):  # Tag exists in top-level of DICOM dataset

                    current_value = values_dict[file_path][0]
                    new_value = process_value(
                        current_value
                    )  # converts to list and types, as appropriate

                    old_value, _ = ds.edit_tag(new_value, tag=tag.tag)
                    history.append([keyword, old_value, new_value])
                else:  # Search entire DICOM dataset for tag
                    addresses = ds.find_tag(tag.tag)
                    if not addresses:
                        raise Exception  # Tag could not be found
                    for a, address in enumerate(addresses):
                        current_value = values_dict[file_path][a]
                        new_value = process_value(
                            current_value
                        )  # converts to list and types

                        old_value, _ = ds.edit_tag(
                            new_value, tag=tag.tag, address=address
                        )
                        history.append([keyword, old_value, new_value])

            except Exception as e:
                err_msg = (
                    "KeyError: %s is not accessible" % tag
                    if str(e).upper() == str(tag).upper()
                    else e
                )
                value = value_str if value_str else "[empty value]"
                modality = (
                    ds.dcm.Modality
                    if hasattr(ds.dcm, "Modality")
                    else "Unknown"
                )
                error_log.append(
                    "Directory: %s\nFile: %s\nModality: %s\n\t"
                    "Attempt to edit %s to new value: %s\n\t%s\n"
                    % (
                        dirname(file_path),
                        basename(file_path),
                        modality,
                        tag,
                        value,
                        err_msg,
                    )
                )

            ds.save_to_file()
            ds.clear_dcm()

    return {
        "error_log": "\n".join(error_log),
        "history": history,
        "ds": data_sets,
    }


def update_referenced_tags(data_sets, check_all_tags, history_row):
    keyword, old_value, new_value = tuple(history_row)
    if "Referenced%s" % keyword in list(keyword_dict):
        for ds in data_sets:
            ds.load_dcm()
            ds.sync_referenced_tag(
                keyword, old_value, new_value, check_all_tags=check_all_tags
            )
            ds.save_to_file()
            ds.clear_dcm()


def value_to_list(value):
    ans = []
    for v in value[1:-1].split(", "):
        if v[0] == "'" and v[-1] == "'":
            ans.append(value[1:-1])
        else:
            ans.append(v)
    return ans


def process_value(value):
    if value[0] == "[" and value[-1] == "]":
        return value_to_list(value)
    return value

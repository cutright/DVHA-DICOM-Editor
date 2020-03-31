#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dynamic_value.py
"""
Apply dynamic value functions
"""
# Copyright (c) 2020 Dan Cutright
# This file is part of DVHA DICOM Editor, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVHA-DICOM-Editor

from os import sep
from os.path import normpath, splitext
from pydicom.uid import generate_uid
from secrets import randbelow


class ValueGenerator:
    """Process function calls in value string"""
    def __init__(self, value=None, tag=None):
        """
        :param value: input tag value from main frame
        :type value: str
        :param tag: the tag to be edited
        """
        self.value = value
        self.tag = tag
        self.enum_instances = {'file': {}, 'value': {}}
        self.uids = {'file': {}, 'value': {}}
        self.rand = {'file': {}, 'value': {}}
        self.data_sets = {}
        self.file_paths = []
        self.func_call = []

        if value is not None and tag is not None:
            self.set_func_call_dict()

        self.functions = ['file', 'val', 'fenum', 'venum', 'fuid', 'vuid', 'frand', 'vrand']
        self.func_map = {f: getattr(self, f) for f in self.functions}

    def __call__(self, data_sets):
        """
        :param data_sets: parsed dicom data using DICOMEditor class
        :return: new tag values
        :rtype: dict
        """
        self.file_paths = sorted(list(data_sets))
        self.data_sets = [data_sets[f] for f in self.file_paths]
        self.set_enum_instances()
        new_values = {}
        for file_path in self.file_paths:
            new_value = self.value.split('*')
            for i, call_str in enumerate(self.value.split('*')):
                if i % 2 == 1:
                    new_value[i] = self.get_value(call_str, file_path)
            new_values[file_path] = ''.join(new_value)
        return new_values

    #################################################################################
    # Setters
    #################################################################################
    def set_func_call_dict(self):
        """Create a dict of functions to input"""
        self.func_call = []
        for f in self.value.split('*')[1::2]:
            func, param = self.split_call_str(f)
            self.func_call.append((func, param))

    def set_enum_instances(self):
        """Collect all unique values for each of the enumerators"""
        self.enum_instances = {'file': {}, 'value': {}}
        for key, instances in self.enum_instances.items():
            functions = [key[0] + f for f in ['enum', 'uid', 'rand']]
            for index in self.get_parameters(functions):
                if key == 'file':
                    enum = [self.file(index, f, True) for f in self.file_paths]
                else:
                    enum = [ds.get_tag_value(self.tag) for ds in self.data_sets]
                instances[index] = sorted(list(set(enum)))

        # set uids
        self.uids = {'file': {}, 'value': {}}
        for key, instances in self.enum_instances.items():
            for index in self.get_parameters(key[0] + 'uid'):
                self.uids[key][index] = {i: generate_uid() for i in self.enum_instances[key][index]}

        # set random numbers
        self.rand = {'file': {}, 'value': {}}
        for key, instances in self.enum_instances.items():
            for index in self.get_parameters(key[0] + 'rand'):
                self.rand[key][index] = {i: str(randbelow(100000)).zfill(5) for i in self.enum_instances[key][index]}

    #################################################################################
    # Getters
    #################################################################################
    def get_parameters(self, functions):
        """Get a the list of parameters for the specified function"""
        parameters = []
        for call_str in self.value.split('*')[1::2]:  # every odd index
            func, param = self.split_call_str(call_str)
            if func in functions:
                parameters.append(param)
        return sorted(list(set(parameters)))

    def get_value(self, call_str, file_path):
        """Parse the function call string, perform the function"""
        func, param = self.split_call_str(call_str)
        if func in list(self.func_map):
            return self.func_map[func](param, file_path)
        return ''

    #################################################################################
    # Utilities
    #################################################################################
    @staticmethod
    def split_call_str(func_call_str):
        """Split the string into function and parameter"""
        f_split = func_call_str.split('[')
        func = f_split[0]
        param = f_split[1][:-1]  # remove last character, ]
        return func, int(param)

    #################################################################################
    # Functions
    #################################################################################
    @staticmethod
    def file(index, file_path, all_up_to_index=False):
        """Process a directory name"""
        components = normpath(file_path).split(sep)
        if all_up_to_index:
            if index == -1:
                return splitext('/'.join(components))[0]
            else:
                return splitext('/'.join(components[:index+1]))[0]
        return splitext(components[index])[0]

    def val(self, index, file_path):
        ds = self.data_sets[self.file_paths.index(file_path)]
        return ds.get_tag_value(self.tag)

    def fenum(self, index, file_path):
        """Process a file enumeration"""
        return str(self.enum_instances['file'][index].index(self.file(index, file_path, True)) + 1)

    def venum(self, index, file_path):
        """Process a value enumeration"""
        ds = self.data_sets[self.file_paths.index(file_path)]
        return str(self.enum_instances['value'][index].index(ds.get_tag_value(self.tag)) + 1)

    def fmethod(self, index, file_path, lookup):
        """Process a file-like function (except enum)"""
        value = self.file(index, file_path, True)
        return lookup['file'][index][value]

    def vmethod(self, index, file_path, lookup):
        """Process a value-like function (except enum)"""
        ds = self.data_sets[self.file_paths.index(file_path)]
        value = ds.get_tag_value(self.tag)
        return lookup['value'][index][value]

    def fuid(self, index, file_path):
        return self.fmethod(index, file_path, self.uids)

    def vuid(self, index, file_path):
        return self.vmethod(index, file_path, self.uids)

    def frand(self, index, file_path):
        return self.fmethod(index, file_path, self.rand)

    def vrand(self, index, file_path):
        return self.vmethod(index, file_path, self.rand)


HELP_TEXT = """--------------------------
Dynamic Value Setting
--------------------------
Users can dynamically define new DICOM tag values based on file path or initial DICOM tag values.

--------------------------
AVAILABLE FUNCTIONS
--------------------------
File path / Tag Value:
        file[n]: the n<sup>th</sup> component of the file path
        val[n]: DICOM tag value, n=-1 being tag value, n=-2 the parent value, etc.

Enumeration:
        fenum[n]: an iterator based on file[n]
        venum[n]: an iterator based on val[n]

DICOM UID
        fuid[n] and vuid[n]: same as fenum/venum, except the enumeration value is replaced with a DICOM compliant UID

Random Number (w/ `secret.randbelow`)
        frand[n] and vrand[n]: same as DICOM UID functions except the value is a random 5-digit integer

NOTE: DICOM tags that are within sequences are not yet enabled, so val, venum, vuid, and vrand functions 
currently ignore n, although n must still be an integer.


--------------------------
EXAMPLES
--------------------------
For a directory /some/file/path/ANON0001/ containing files file_1.dcm, file_2.dcm:
Directory:
        NOTE: file extensions are removed
        some_string_*file[-1]*
                    some_string_file_1
                    some_string_file_2
        *file[-2]*_AnotherString
                    ANON0001_AnotherString
                    ANON0001_AnotherString
File Enumeration:
        some_string_*fenum[-1]*
                    some_string_1
                    some_string_2
        *fenum[-2]*_AnotherString
                1_AnotherString
                1_AnotherString
Value Enumeration:
        NOTE: Assume each file has the same StudyInstanceUID but different SOPInstanceUIDs
        *file[-2]*_*venum[-1]* used with SOPInstanceUID tag
                ANON0001_1
                ANON0001_2
        *file[-2]*_*venum[-1]* used with StudyInstanceUID tag
                ANON0001_1
                ANON0001_1
"""

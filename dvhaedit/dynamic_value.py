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
from pubsub import pub
from pydicom.uid import generate_uid
from secrets import randbelow
from dvhaedit.paths import DYNAMIC_VALUE_HELP


class ValueGenerator:
    """Process function calls in value string"""
    def __init__(self, value=None, tag=None, options=None):
        """
        :param value: input tag value from main frame
        :type value: str
        :param tag: the tag to be edited
        """
        self.value = value
        self.tag = tag
        self.options = options
        self.enum_instances = {'file': {}, 'value': {}}
        self.uids = {'file': {}, 'value': {}}
        self.rand = {'file': {}, 'value': {}}
        self.data_sets = {}
        self.file_paths = []
        self.func_call = []

        self.functions = ['file', 'val', 'fenum', 'venum', 'fuid', 'vuid', 'frand', 'vrand']
        self.value_functions = [f for f in self.functions if f[0] == 'v']
        self.func_map = {f: getattr(self, f) for f in self.functions}

        if value is not None and tag is not None:
            self.set_func_call_dict()

    def __call__(self, data_sets, file_path=None, callback=None):
        """
        :param data_sets: parsed dicom data using DICOMEditor class
        :type data_sets: dict
        :param file_path: optionally specify a single file_path for the generator to use (for efficient previewing)
        :type file_path: str
        :param callback: optional function call through each loop through files, two parameters (iteration, count_total)
        :return: new tag values
        :rtype: dict or str
        """
        if file_path is None:
            self.file_paths = sorted(list(data_sets))
        else:
            self.file_paths = [file_path]
        self.data_sets = [data_sets[f] for f in self.file_paths]

        file_count = len(self.file_paths)
        self.set_enum_instances()
        new_values = {}

        self.value_generator_callback(0, file_count)

        for f_counter, f in enumerate(self.file_paths):
            new_value = self.value.split('*')
            for i, call_str in enumerate(self.value.split('*')):
                if i % 2 == 1:
                    new_value[i] = str(self.get_value(call_str, f))
            new_values[f] = ''.join(new_value)

            self.value_generator_callback(f_counter+1, file_count)

        if file_path is not None:
            return new_values[file_path]
        return new_values

    @staticmethod
    def value_generator_callback(iteration, count_total):
        msg = {'label': 'Calculating values for file %s of %s' % (iteration, count_total),
               'gauge': iteration / count_total}
        pub.sendMessage("progress_update", msg=msg)

    #################################################################################
    # Setters
    #################################################################################
    def set_func_call_dict(self):
        """Create a dict of functions to input"""
        self.func_call = []
        for f in str(self.value).split('*')[1::2]:
            func, param = self.split_call_str(f)
            self.func_call.append((func, param))

    @staticmethod
    def send_progress_update(progress, label='Initializing...'):
        msg = {'label': label,
               'gauge': progress}
        pub.sendMessage("progress_update", msg=msg)

    def set_enum_instances(self):
        """Collect all unique values for each of the enumerators"""
        self.send_progress_update(0)
        # Determine how many actions to perform, for progress indication
        count = 0
        self.enum_instances = {'file': {}, 'value': {}}
        for key in list(self.enum_instances):
            functions = [key[0] + f for f in ['enum', 'uid', 'rand']]
            parameters = self.get_parameters(functions)
            for _ in parameters:
                if key == 'file':
                    count += 1
                else:
                    count += len(self.data_sets)

        counter = 0.
        for key, instances in self.enum_instances.items():
            functions = [key[0] + f for f in ['enum', 'uid', 'rand']]
            parameters = self.get_parameters(functions)
            for index in parameters:
                if key == 'file':
                    enum = [self.file(index, f, True) for f in self.file_paths]
                    self.send_progress_update(counter / count)
                    counter += 1
                else:
                    enum = []
                    for ds in self.data_sets:
                        enum.extend(ds.get_all_tag_values(self.tag))
                        enum = list(set(enum))
                        self.send_progress_update(counter / count)
                        counter += 1
                instances[index] = sorted(list(set(enum)))

        # set uids
        prefix = self.options.prefix if hasattr(self.options, 'prefix') else None
        if prefix == '':
            prefix = None
        entropy_srcs = [self.options.entropy_source] if hasattr(self.options, 'entropy_source') else None
        if entropy_srcs == '':
            entropy_srcs = None
        self.uids = {'file': {}, 'value': {}}
        for key, instances in self.enum_instances.items():
            for index in self.get_parameters(key[0] + 'uid'):
                self.send_progress_update(0.95, label='Generating UIDs...')
                self.uids[key][index] = {i: generate_uid(prefix=prefix, entropy_srcs=entropy_srcs)
                                         for i in self.enum_instances[key][index]}

        # set random numbers
        digits = self.options.rand_digits if hasattr(self.options, 'rand_digits') else 5
        max_num = 10 ** digits
        self.rand = {'file': {}, 'value': {}}
        for key, instances in self.enum_instances.items():
            for index in self.get_parameters(key[0] + 'rand'):
                self.send_progress_update(0.98, label='Generating random numbers...')
                self.rand[key][index] = {i: str(randbelow(max_num)).zfill(digits)
                                         for i in self.enum_instances[key][index]}

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
    def split_call_str(self, func_call_str):
        """Split the string into function and parameter"""
        if func_call_str in self.value_functions:
            return func_call_str, None
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

    # The following function names, in this comment block, must match those found in self.functions,
    # and have two input parameters: index and file_path

    def val(self, _, file_path):
        """Process a value enumeration (index included for abstract use)"""
        ds = self.data_sets[self.file_paths.index(file_path)]
        try:
            return ds.get_tag_value(self.tag)
        except KeyError:
            addresses = ds.find_tag(self.tag)
            if addresses:
                return addresses[0][-1][1]
            return None

    def fenum(self, index, file_path):
        """Process a file enumeration"""
        return str(self.enum_instances['file'][index].index(self.file(index, file_path, True)) + 1)

    def venum(self, index, file_path):
        """Process a value enumeration"""
        ds = self.data_sets[self.file_paths.index(file_path)]
        try:
            value = ds.get_tag_value(self.tag)
        except KeyError:
            addresses = ds.find_tag(self.tag)
            if addresses:
                value = addresses[0][-1][1]
            else:
                return 'None'
        return str(self.enum_instances['value'][index].index(value) + 1)

    def fuid(self, index, file_path):
        """Process file path based uid generator"""
        return self.fmethod(index, file_path, self.uids)

    def vuid(self, index, file_path):
        """Process value based uid generator"""
        return self.vmethod(index, file_path, self.uids)

    def frand(self, index, file_path):
        """Process file path based random number generator"""
        return self.fmethod(index, file_path, self.rand)

    def vrand(self, index, file_path):
        """Process value based random number generator"""
        return self.vmethod(index, file_path, self.rand)

    # Helper functions for file and value type functions above, to reduce repeated code
    def fmethod(self, index, file_path, lookup):
        """Process a file-like function (except enum)"""
        value = self.file(index, file_path, True)
        return lookup['file'][index][value]

    def vmethod(self, index, file_path, lookup):
        """Process a value-like function (except enum)"""
        ds = self.data_sets[self.file_paths.index(file_path)]
        try:
            value = ds.get_tag_value(self.tag)
        except KeyError:
            addresses = ds.find_tag(self.tag)
            if addresses:
                value = addresses[0][-1][1]
            else:
                return None
        return lookup['value'][index][value]


with open(DYNAMIC_VALUE_HELP, 'r') as doc:
    HELP_TEXT = doc.read()

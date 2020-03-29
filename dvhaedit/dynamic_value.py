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


class ValueGenerator:
    def __init__(self, value):
        self.value = value
        self.enum_instances = {}

        self.__set_func_call_dict()

        self.func_map = {'dir': self.dir,
                         'enum': self.enum}

    def __call__(self, file_paths):
        self.set_enum_instances(file_paths)
        new_values = {}
        for file_path in file_paths:
            new_value = self.value.split('*')
            for i, call_str in enumerate(self.value.split('*')):
                if i % 2 == 1:
                    new_value[i] = self.do_func_call(call_str, file_path)
            new_values[file_path] = ''.join(new_value)
        return new_values

    def do_func_call(self, call_str, file_path):
        func, param = self.split_call_str(call_str)
        if func in list(self.func_map):
            return self.func_map[func](param, file_path)
        return ''

    @staticmethod
    def split_call_str(func_call_str):
        f_split = func_call_str.split('[')
        func = f_split[0]
        param = f_split[1][:-1]  # remove last character, ]
        return func, int(param)

    def __set_func_call_dict(self):
        """Create a dict of functions to input"""
        # function calls exist between asterisks
        self.func_call = []
        for f in self.value.split('*')[1::2]:
            func, param = self.split_call_str(f)
            self.func_call.append((func, param))

    @staticmethod
    def dir(index, file_path, all_up_to_index=False):
        components = normpath(file_path).split(sep)
        if all_up_to_index:
            if index == -1:
                return splitext('/'.join(components))[0]
            else:
                return splitext('/'.join(components[:index+1]))[0]
        return splitext(components[index])[0]

    def set_enum_instances(self, file_paths):
        self.enum_instances = {}
        for index in self.enum_param:
            enum = [self.dir(index, f, True) for f in file_paths]
            self.enum_instances[index] = sorted(list(set(enum)))

    def enum(self, index, file_path):
        return str(self.enum_instances[index].index(self.dir(index, file_path, True))+1)

    @property
    def enum_param(self):
        parameters = []
        for call_str in self.value.split('*')[1::2]:  # every odd index
            func, param = self.split_call_str(call_str)
            if func == 'enum':
                parameters.append(param)
        return parameters

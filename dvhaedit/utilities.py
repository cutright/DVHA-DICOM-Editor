#!/usr/bin/env python
# -*- coding: utf-8 -*-

# utilities.py
"""
General utilities borrowed from DVH Analytics
"""
# Copyright (c) 2016-2020 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics


import wx
from os import walk, listdir
from os.path import isfile, isdir, splitext, join


def get_file_paths(start_path, search_sub_folders=False, extension=None):
    """
    Get a list of absolute file paths for a given directory
    :param start_path: initial directory
    :type start_path str
    :param search_sub_folders: optionally search all sub folders
    :type search_sub_folders: bool
    :param extension: optionally include only files with specified extension
    :type extension: str
    :return: absolute file paths
    :rtype: list
    """

    ignored_files = ['.ds_store']

    if isdir(start_path):
        if search_sub_folders:
            file_paths = []
            for root, dirs, files in walk(start_path, topdown=False):
                for name in files:
                    if extension is None or splitext(name)[1].lower() == extension.lower():
                        if name.lower() not in ignored_files:
                            file_paths.append(join(root, name))
            return file_paths

        file_paths = []
        for f in listdir(start_path):
            if isfile(join(start_path, f)):
                if extension is None or splitext(f)[1].lower() == extension.lower():
                    if f.lower() not in ignored_files:
                        file_paths.append(join(start_path, f))
        return file_paths
    return []


def get_selected_listctrl_items(list_control):
    """
    Get the indices of the currently selected items of a wx.ListCtrl object
    :param list_control: any wx.ListCtrl object
    :type list_control: ListCtrl
    :return: indices of selected items
    :rtype: list
    """
    selection = []

    index_current = -1
    while True:
        index_next = list_control.GetNextItem(index_current, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if index_next == -1:
            return selection

        selection.append(index_next)
        index_current = index_next


def get_sorted_indices(some_list):
    try:
        return [i[0] for i in sorted(enumerate(some_list), key=lambda x: x[1])]
    except TypeError:  # can't sort if a mix of str and float
        try:
            temp_data = [[value, -float('inf')][value == 'None'] for value in some_list]
            return [i[0] for i in sorted(enumerate(temp_data), key=lambda x: x[1])]
        except TypeError:
            temp_data = [str(value) for value in some_list]
            return [i[0] for i in sorted(enumerate(temp_data), key=lambda x: x[1])]


def is_windows():
    return wx.Platform == '__WXMSW__'


def set_msw_background_color(parent):
    if is_windows():
        parent.SetBackgroundColour('lightgrey')


def is_linux():
    return wx.Platform == '__WXGTK__'


def is_mac():
    return wx.Platform == '__WXMAC__'


def get_window_size(width, height):
    """
    Function used to adapt frames/windows for the user's resolution
    :param width: fractional width of the user's screen
    :param height: fractional height of the user's screen
    :return: window size
    :rtype: tuple
    """
    user_width, user_height = wx.GetDisplaySize()
    if user_width / user_height < 1.5:  # catch 4:3 or non-widescreen
        user_height = user_width / 1.6
    return tuple([int(width * user_width), int(height * user_height)])


def get_type(type_str):
    type_map = {'float': float, 'int': int, 'str': str}
    if type_str.lower() in list(type_map):
        return type_map[type_str.lower()]
    return str


def save_csv_to_file(csv_data, abs_file_path):
    """
    Save a python object acceptable for pickle to the provided file path
    """
    with open(abs_file_path, 'w') as outfile:
        outfile.write(csv_data)


def load_csv_from_file(abs_file_path):
    """
    Load a pickled object from the provided absolute file path
    """
    columns, data = None, None
    if isfile(abs_file_path):
        with open(abs_file_path, 'r') as infile:
            columns = [c.strip() for c in infile.readline().split(',')]
            data = {c: [] for c in columns}
            for row in infile:
                for i, value in enumerate(row.split(',')):
                    data[columns[i]].append(value.strip().replace(';', ','))

    return columns, data


class ErrorDialog:
    def __init__(self, parent, message, caption, flags=wx.ICON_ERROR | wx.OK | wx.OK_DEFAULT):
        """
        This class allows error messages to be called with a one-liner else-where
        :param parent: wx parent object
        :param message: error message
        :param caption: error title
        :param flags: flags for wx.MessageDialog
        """
        self.dlg = wx.MessageDialog(parent, message, caption, flags)
        self.dlg.Center()
        self.dlg.ShowModal()
        self.dlg.Destroy()

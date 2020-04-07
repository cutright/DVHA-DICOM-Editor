#!/usr/bin/env python
# -*- coding: utf-8 -*-

# threads.py
"""
Expensive calculations for main app that merit threading
"""
# Copyright (c) 2020 Dan Cutright
# This file is part of DVHA DICOM Editor, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVHA-DICOM-Editor

from functools import partial
from os.path import basename, dirname
from pubsub import pub
from pydicom.datadict import keyword_dict
from dvhaedit.dicom_editor import DICOMEditor, save_dicom
from dvhaedit.threading import ProgressFrame


#################################################################################
# Simple threads with a single function performed on each item the provided list
#################################################################################

class ParsingProgressFrame(ProgressFrame):
    """Create a window to display DICOM file parsing progress and begin ParseWorker"""
    def __init__(self, file_paths):
        ProgressFrame.__init__(self, file_paths, DICOMEditor, close_msg='parse_complete',
                               action_msg='add_parsed_data', action_gui_phrase='Parsing File',
                               title='Reading DICOM Headers')


class SavingProgressFrame(ProgressFrame):
    """Create a window to display DICOM file saving progress and begin SaveWorker"""
    def __init__(self, data_sets):
        ProgressFrame.__init__(self, data_sets, save_dicom, close_msg='save_complete',
                               action_gui_phrase='Saving File',
                               title='Saving DICOM Data')


#################################################################################
# Modified threading implementation
#################################################################################

# ------------------------------------------------------------------------------
# Referenced tag searching and updating
# ------------------------------------------------------------------------------
# TODO: Can update_referenced_tags be a function in main?
class RefSyncProgressFrame(ProgressFrame):
    """Create a window to display Referenced tag syncing progress and begin SaveWorker"""
    def __init__(self, history, data_sets, check_all_tags):
        ProgressFrame.__init__(self, history, partial(update_referenced_tags, data_sets, check_all_tags),
                               close_msg='ref_sync_complete',
                               action_gui_phrase='Checking References for Tag:',
                               title='Checking for Referenced Tags')


def update_referenced_tags(data_sets, check_all_tags, history_row):
    keyword, old_value, new_value = tuple(history_row)
    if "Referenced%s" % keyword in list(keyword_dict):
        for ds in data_sets:
            ds.sync_referenced_tag(keyword, old_value, new_value, check_all_tags=check_all_tags)


# ------------------------------------------------------------------------------
# Value Generator calls GUI progress updates and the provided list is only one item
# ------------------------------------------------------------------------------
class ValueGenProgressFrame(ProgressFrame):
    """Create a window to display value generation progress and begin SaveWorker"""
    def __init__(self, data_sets, value_generator, iteration, total_count):

        ProgressFrame.__init__(self, [data_sets], value_generator,
                               close_msg='value_gen_complete',
                               action_msg='add_value_dicts',
                               action_gui_phrase='File:',
                               title='Generating Values for Tag %s of %s' % (iteration, total_count))


# ------------------------------------------------------------------------------
# Modified to handle nested for loops in apply_edits
# ------------------------------------------------------------------------------
class ApplyEditsProgressFrame(ProgressFrame):
    """Create a window to display value generation progress and begin SaveWorker"""
    def __init__(self, data_sets, values_dicts, all_row_data):

        ProgressFrame.__init__(self, [data_sets], partial(apply_edits, values_dicts, all_row_data),
                               close_msg='do_save_dicom',
                               action_msg='update_dicom_edits',
                               action_gui_phrase='',
                               title='Editing DICOM Data')


def apply_edits(values_dicts, all_row_data, data_sets):
    """Apply the tag edits to every file in self.ds, return any errors"""
    error_log, history = [], []
    for row in range(len(all_row_data)):

        row_data = all_row_data[row]
        tag = row_data['tag']
        value_str = row_data['value_str']
        keyword = row_data['keyword']
        value_type = row_data['value_type']
        values_dict = values_dicts[row]

        for i, (file_path, ds) in enumerate(data_sets.items()):
            label = "Editing %s for file %s of %s" % (keyword, i+1, len(data_sets))
            msg = {'label': label, 'gauge': float(i) / len(data_sets)}
            pub.sendMessage("progress_update", msg=msg)
            try:
                if tag.tag in ds.dcm.keys():
                    new_value = value_type(values_dict[file_path])
                    old_value, _ = ds.edit_tag(new_value, tag=tag.tag)
                    history.append([keyword, old_value, new_value])
                else:
                    addresses = ds.find_tag(tag.tag)
                    if not addresses:
                        raise Exception
                    for address in addresses:
                        new_value = value_type(values_dict[file_path])
                        old_value, _ = ds.edit_tag(new_value, tag=tag.tag, address=address)
                        history.append([keyword, old_value, new_value])

            except Exception as e:
                err_msg = 'KeyError: %s is not accessible' % tag if str(e).upper() == str(tag).upper() else e
                value = value_str if value_str else '[empty value]'
                modality = ds.dcm.Modality if hasattr(ds.dcm, 'Modality') else 'Unknown'
                error_log.append("Directory: %s\nFile: %s\nModality: %s\n\t"
                                 "Attempt to edit %s to new value: %s\n\t%s\n" %
                                 (dirname(file_path), basename(file_path), modality, tag, value, err_msg))

    return {'error_log': '\n'.join(error_log),
            'history': history,
            'ds': data_sets}

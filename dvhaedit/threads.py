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
from dvhaedit.dicom_editor import DICOMEditor, save_dicom, apply_edits, update_referenced_tags
from dvhaedit.threading import ProgressFrame


#################################################################################
# Simple threads with a single function performed on each item the provided list
#################################################################################

class ParsingProgressFrame(ProgressFrame):
    """Create a window to display DICOM file parsing progress and begin ParseWorker"""
    def __init__(self, file_paths, force_open):
        kwargs_list = [{'dcm': f, 'force': force_open} for f in file_paths]
        ProgressFrame.__init__(self, kwargs_list, DICOMEditor, close_msg='parse_complete',
                               action_msg='add_parsed_data', action_gui_phrase='Parsing File',
                               title='Reading DICOM Headers', kwargs=True)


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
class RefSyncProgressFrame(ProgressFrame):
    """Create a window to display Referenced tag syncing progress and begin SaveWorker"""
    def __init__(self, history, data_sets, check_all_tags):
        ProgressFrame.__init__(self, history, partial(update_referenced_tags, data_sets, check_all_tags),
                               close_msg='ref_sync_complete',
                               action_gui_phrase='Checking References for Tag:',
                               title='Checking for Referenced Tags')


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
    # Input list is only one item, the apply edits function send GUI updates to ProgressFrame
    def __init__(self, data_sets, values_dicts, all_row_data):

        ProgressFrame.__init__(self, [data_sets], partial(apply_edits, values_dicts, all_row_data),
                               close_msg='do_save_dicom',
                               action_msg='update_dicom_edits',
                               action_gui_phrase='',
                               title='Editing DICOM Data')
